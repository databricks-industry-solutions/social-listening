import pandas as pd
from databricks import sql
from databricks.sdk.core import Config
import flask
from contextlib import contextmanager
import signal
from functools import wraps
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


DEFAULT_TIMEOUT_s = 10

def timeout_handler(signum, frame):
    raise TimeoutError("Database query timed out")

def with_timeout(seconds):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Set the timeout handler
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                # Disable the alarm
                signal.alarm(0)
            return result
        return wrapper
    return decorator

class DataLoader:
    def __init__(self, cfg: Config, catalog_name: str, schema_name: str):
        # Initialize Databricks config
        self.cfg = cfg
        self.profile_name = cfg.profile
        self.hostname = cfg.hostname
        logger.info(f"DataLoader: Current Databricks profile: {self.profile_name}")
        logger.info(f"DataLoader: Current Databricks hostname: {self.hostname}")

        self.catalog_name = catalog_name
        self.schema_name = schema_name

        self.game_reviews_table_name = 'feedback_content_gold'
        self.game_review_reports_table_name = 'feedback_content_reports'

        logger.info(f"DataLoader: Catalog/Schema to read from: {self.catalog_name}.{self.schema_name}")
        logger.info(f"DataLoader: Warehouse ID: {self.cfg.warehouse_id}")

    # Query the SQL warehouse with Service Principal credentials
    def sql_query_with_service_principal(self, query: str) -> pd.DataFrame:
        """Execute a SQL query and return the result as a pandas DataFrame."""
        # cfg = Config()
        connection = None
        cursor = None

        try:
            connection = sql.connect(
                server_hostname=self.cfg.host,
                http_path=f"/sql/1.0/warehouses/{self.cfg.warehouse_id}",
                credentials_provider=lambda: self.cfg.authenticate,  # Uses SP credentials from the environment variables
                _socket_timeout=DEFAULT_TIMEOUT_s  # Add socket timeout
            )
            cursor = connection.cursor()
            cursor.execute(query)
            result = cursor.fetchall_arrow().to_pandas()
            return result
        except TimeoutError:
            logger.warning("DataLoader: Query timed out")
            return None
        except Exception as e:
            logger.warning(f"DataLoader: SQL query failed: {str(e)}")
            return None
        finally:
            # Explicitly close cursor and connection
            if cursor:
                try:
                    cursor.close()
                except Exception as e:
                    logger.warning(f"Error closing cursor: {e}")
            if connection:
                try:
                    connection.close()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
            
    # Query the SQL warehouse with the user credentials
    # @with_timeout(DEFAULT_TIMEOUT_s)
    def sql_query_with_user_token(self, query: str, user_token: str) -> pd.DataFrame:
        """Execute a SQL query and return the result as a pandas DataFrame."""
        # cfg = Config()
        connection = None
        cursor = None

        try:
            connection = sql.connect(
                server_hostname=self.cfg.host,
                http_path=f"/sql/1.0/warehouses/{self.cfg.warehouse_id}",
                access_token=user_token,
                _socket_timeout=DEFAULT_TIMEOUT_s  # Add socket timeout
            )
            cursor = connection.cursor()
            cursor.execute(query)
            result = cursor.fetchall_arrow().to_pandas()
            return result
        except TimeoutError:
            logger.warning("DataLoader: Query timed out")
            return None
        except Exception as e:
            logger.warning(f"DataLoader: SQL query failed: {str(e)}")
            return None
        finally:
            # Explicitly close cursor and connection
            if cursor:
                try:
                    cursor.close()
                except Exception as e:
                    logger.warning(f"Error closing cursor: {e}")
            if connection:
                try:
                    connection.close()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
    
    @staticmethod
    def clean_game_name(game_name: str) -> str:
        """Clean the game name to remove any special characters (for SQL queries)."""
        return game_name.replace("'", "''")
    
    def get_user_token(self) -> str:
        """Get the user access token from the request headers."""
        return flask.request.headers.get('X-Forwarded-Access-Token')

    def load_game_data(self, game_name: str, use_user_token: bool=False) -> pd.DataFrame:
        """Load game data from the database."""
        logger.info(f"Loading data for game: {game_name}")
        # clean_game_name = self.clean_game_name(game_name)
        query = f"""
            SELECT * FROM {self.catalog_name}.{self.schema_name}.{self.game_reviews_table_name} 
            WHERE game_name = "{game_name}"
        """
        return self._load_data(query, use_user_token)

    def load_game_review_reports(self, game_name: str, use_user_token: bool=False) -> pd.DataFrame:
        """Load game review reports from the database."""
        logger.info(f"Loading game review reports for game: {game_name}")
        # clean_game_name = self.clean_game_name(game_name)
        query = f"""
            SELECT * FROM {self.catalog_name}.{self.schema_name}.{self.game_review_reports_table_name} 
            WHERE game_name = "{game_name}"
            """
        return self._load_data(query, use_user_token)

    def get_game_names(self, use_user_token: bool=False) -> list[dict[str, str]]:
        """
        Get the list of unique game names and content types from the database.
        Returns a list of dictionaries in the form: [{"game_name": "...", "content_type": "..."}, ...]
        """
        query = f"SELECT DISTINCT game_name, content_type FROM {self.catalog_name}.{self.schema_name}.{self.game_reviews_table_name}"
        games_df = self._load_data(query, use_user_token)
        if games_df is None:
            return None
        return games_df.to_dict(orient='records')
    
    def get_persona_names(self, game_name: str,use_user_token: bool=False) -> list[str]:
        """Get the list of unique persona names from the database."""
        query = f"""
            SELECT DISTINCT persona FROM {self.catalog_name}.{self.schema_name}.{self.game_review_reports_table_name}
            WHERE game_name = '{game_name}'
            """
        personas_df = self._load_data(query, use_user_token)
        if personas_df is None:
            return None
        return personas_df['persona'].unique().tolist()

    def _load_data(self, query: str, use_user_token: bool=False) -> pd.DataFrame:
        """Load data from the database."""
        try:
            logger.info(f"DataLoader: Loading data with query: {query}")
            if use_user_token:
                user_token = self.get_user_token()
                if not user_token:
                    logger.warning("DataLoader: Missing access token in headers")
                    return None
                else:
                    return self.sql_query_with_user_token(query, user_token=user_token)
            else:
                return self.sql_query_with_service_principal(query)
        except Exception as e:
            logger.warning(f"DataLoader: Data load failed: {str(e)}")
            return None