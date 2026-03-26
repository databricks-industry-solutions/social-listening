import os
import time
import logging

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from databricks.sdk.service import jobs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabricksClient:
    def __init__(self, cfg: Config, ingestion_job_id: str):
        self.cfg = cfg
        self.workspace_client = WorkspaceClient()
        self.ingestion_job_id = ingestion_job_id

        self.generic_table_required_format = [
            {"name": "content_id", "type": "string"},
            {"name": "content_type", "type": "string"},
            {"name": "game_name", "type": "string"},
            {"name": "content_text", "type": "string"},
            {"name": "timestamp", "type": "timestamp"},
            {"name": "author_id", "type": "string"},
            {"name": "content_metadata", "type": "string"}
        ]

    def get_workspace_client(self):
        return self.workspace_client

    def get_ingestion_job_info(self):
        # Returns a DBX SDK Job object
        job = self.workspace_client.jobs.get(job_id=self.ingestion_job_id)
        logger.info(f"DatabricksClient: Ingestion job info: {job}")
        return job

    def get_job_run_info(self, run_id) -> dict:
        raw_info = self.workspace_client.jobs.get_run(run_id)
        run_info = {
            "run_id": run_id,
            "run_name": raw_info.run_name,
            "run_page_url": raw_info.run_page_url,
            "run_start_time": raw_info.start_time
        }
        return run_info

    def run_ingestion_job(self, source_content_id: str, content_type: str, game_name: str, update_type: str="NEW_GAME") -> dict:
        """
        Triggers a new ingestion job run with the given parameters.
        Returns a dictionary of information about the triggered run.
        """
        job_params = {
            "update_type": update_type,
            "source_content_id": source_content_id,
            "content_type": content_type,
            "game_name": game_name
        }
        job_run_waiter = self.workspace_client.jobs.run_now(
            job_id=self.ingestion_job_id,
            job_parameters=job_params
        )
        job_run_info = self.get_job_run_info(job_run_waiter.run_id)
        logger.info(f"DatabricksClient: Ingestion job run info: {job_run_info}")
        return job_run_info

    def check_table_exists(self, catalog: str, schema: str, table: str) -> bool:
        """
        Checks if a table exists in the Databricks workspace.
                    
        Returns:
            True if table exists, False otherwise
        """
        table_path = f"{catalog}.{schema}.{table}"
        try:
            self.workspace_client.tables.get(table_path)
            logger.info(f"Table exists: {table_path}")
            return True
            
        except Exception as e:
            logger.warning(f"Table does not exist or error checking: {table_path}. Error: {str(e)}")
            return False
    
    def get_table_column_info(self, catalog: str, schema: str, table: str) -> list:
        """
        Gets the column information for the given table.
        """
        table_path = f"{catalog}.{schema}.{table}"
        table_object = self.workspace_client.tables.get(table_path)
        col_info = []
        for col in table_object.columns:
            info_dict = {"name": col.name, "type": col.type_text}
            col_info.append(info_dict)
        return col_info

    def check_generic_table(self, catalog: str, schema: str, table: str) -> bool:
        """
        Checks if the given table satisfies the format for ingestion.
        """
        col_info = self.get_table_column_info(catalog, schema, table)

        # Soft check, just check column names are present
        col_names = [col["name"] for col in col_info]
        required_col_names = [col["name"] for col in self.generic_table_required_format]
        for required_col_name in required_col_names:
            if required_col_name not in col_names:
                return False
        return True
    
    def get_generic_table_required_format(self) -> list:
        """
        Returns the required format for generic table ingestion.
        
        Returns:
            List of dictionaries containing column name and type
        """
        return self.generic_table_required_format
