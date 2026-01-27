import os
import logging
import yaml
from pathlib import Path
from databricks.sdk.core import Config
from utils.data import DataLoader
from utils.databricks import DatabricksClient
from utils.steam import SteamHelper
from utils.google_play import GooglePlayHelper
from utils.reddit import RedditHelper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the path to the HTML template file
TEMPLATE_PATH = Path(__file__).parent / "templates" / "index.html"

# Open main app config file
config_file_path = "config.yaml"
with open(config_file_path, 'r') as config_file:
    CONFIG_DATA = yaml.safe_load(config_file)

    dashboard_url_data = CONFIG_DATA['databricks']['dashboard']['url']
    DASHBOARD_BASE_URL = dashboard_url_data['base']
    DASHBOARD_URL_GAME_FILTER_SUFFIX = dashboard_url_data['game_filter_suffix']
    DASHBOARD_URL_CATEGORY_PAGE_GAME_FILTER_SUFFIX = dashboard_url_data['category_page_game_filter_suffix']

    CATALOG_NAME = CONFIG_DATA['databricks']['catalog']
    SCHEMA_NAME = CONFIG_DATA['databricks']['schema']

# Initialize DataLoader
try:
    cfg = Config()
    data_loader = DataLoader(cfg, catalog_name=CATALOG_NAME, schema_name=SCHEMA_NAME)
    logger.info("Successfully initialized DataLoader")
except Exception as e:
    logger.error(f"Failed to initialize DataLoader: {e}")
    data_loader = None

# Initialize DatabricksClient
try:
    cfg = Config()
    ingestion_job_id = CONFIG_DATA['databricks']['ingestion_job_id']
    logger.info(f"Read ingestion job ID from config file: {ingestion_job_id}")
    databricks_client = DatabricksClient(cfg, ingestion_job_id=ingestion_job_id)
    logger.info("Successfully initialized DatabricksClient")
except Exception as e:
    logger.error(f"Failed to initialize DatabricksClient: {e}")
    databricks_client = None

# Initialize SteamHelper
try:
    steam_api_key = os.environ.get('STEAM_API_KEY')
    if steam_api_key:
        steam_helper = SteamHelper(steam_api_key)
    else:
        logger.warning("Steam API key not found in environment variables")
        steam_helper = SteamHelper()
    logger.info("Successfully initialized SteamHelper")
except Exception as e:
    logger.error(f"Failed to initialize SteamHelper: {e}")
    steam_helper = None

# Initialize GooglePlayHelper
try:
    google_play_helper = GooglePlayHelper()
    logger.info("Successfully initialized GooglePlayHelper")
except Exception as e:
    logger.error(f"Failed to initialize GooglePlayHelper: {e}")
    google_play_helper = None

# Initialize RedditHelper
try:
    reddit_client_id = os.environ.get('REDDIT_CLIENT_ID')
    reddit_client_secret = os.environ.get('REDDIT_CLIENT_SECRET')
    reddit_user_agent = os.environ.get('REDDIT_USER_AGENT')
    
    if reddit_client_id and reddit_client_secret and reddit_user_agent:
        reddit_helper = RedditHelper(reddit_client_id, reddit_client_secret, reddit_user_agent)
        logger.info("Successfully initialized RedditHelper")
    else:
        logger.warning("Reddit credentials not found in environment variables")
        reddit_helper = None
except Exception as e:
    logger.error(f"Failed to initialize RedditHelper: {e}")
    reddit_helper = None

# DEPENDENCY FUNCTIONS

async def get_template_path() -> Path:
    return TEMPLATE_PATH

async def get_dashboard_url_info() -> dict:
    return {
        'base': DASHBOARD_BASE_URL,
        'game_filter_suffix': DASHBOARD_URL_GAME_FILTER_SUFFIX,
        'category_page_game_filter_suffix': DASHBOARD_URL_CATEGORY_PAGE_GAME_FILTER_SUFFIX
    }

async def get_data_loader() -> DataLoader:
    return data_loader

async def get_databricks_client() -> DatabricksClient:
    return databricks_client

async def get_steam_helper() -> SteamHelper:
    return steam_helper

async def get_google_play_helper() -> GooglePlayHelper:
    return google_play_helper

async def get_reddit_helper() -> RedditHelper:
    return reddit_helper