import logging
import os
from enum import Enum

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from utils.steam import SteamHelper
from utils.databricks import DatabricksClient
from dependencies import get_steam_helper, set_steam_helper, get_databricks_client, get_secret_scope, get_steam_api_key_secret_key
from schemas import steam as steam_schemas

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/steam")


class SteamCredentialsTestStatus(Enum):
    """Result of testing Steam API credentials."""
    VALID = 1
    INVALID = 2
    NOT_CONFIGURED = 3


def test_steam_credentials(api_key: str | None = None) -> tuple[SteamCredentialsTestStatus, SteamHelper | None]:
    """
    Test Steam API credentials by instantiating SteamHelper.

    Args:
        api_key: Steam API key to use. If None, uses the STEAM_API_KEY environment variable.

    Returns:
        Tuple of (status, helper): status is SUCCESS, FAIL, or NOT_CONFIGURED;
            helper is the SteamHelper instance on SUCCESS, None otherwise.
    """
    key = api_key
    if key is None:
        key = os.environ.get("STEAM_API_KEY")
    if not key or key == "":
        return (SteamCredentialsTestStatus.NOT_CONFIGURED, None)
    try:
        helper = SteamHelper(api_key=key)
        return (SteamCredentialsTestStatus.VALID, helper)
    except Exception as e:
        return (SteamCredentialsTestStatus.INVALID, None)


@router.get('/test-credentials')
async def test_steam_credentials_endpoint(
    api_key: str | None = Header(None, description="Steam API key to test; if omitted, uses STEAM_API_KEY env var"),
    databricks_client: DatabricksClient | None = Depends(get_databricks_client),
    secret_scope: str | None = Depends(get_secret_scope),
    steam_secret_key: str | None = Depends(get_steam_api_key_secret_key),
):
    """
    Test Steam API credentials. Returns status: valid, invalid, or not_configured.
    On valid, updates the app's SteamHelper, the STEAM_API_KEY env var, and (if available) the Databricks secret.
    """
    result, steam_helper = test_steam_credentials(api_key=api_key)
    if result == SteamCredentialsTestStatus.VALID and steam_helper is not None:
        key_value = steam_helper.api_key
        if key_value:
            os.environ["STEAM_API_KEY"] = key_value
        set_steam_helper(steam_helper)
        if databricks_client is not None and secret_scope and steam_secret_key:
            try:
                databricks_client.put_secret(scope=secret_scope, key=steam_secret_key, string_value=key_value or "")
                logger.info("Updated Databricks secret %s/%s", secret_scope, steam_secret_key)
            except Exception as e:
                logger.warning("Could not update Databricks secret: %s", e)
        logger.info("Updated app SteamHelper with tested/valid credentials")
    return {"status": result.name.lower()}

@router.get('/search', response_model=steam_schemas.SteamSearchResponse)
async def search_steam_games(query: str = Query(..., min_length=1, description="Search query for Steam games"),
                             steam_helper: SteamHelper = Depends(get_steam_helper)):
    """
    API endpoint to search for Steam games.
    
    Args:
        query: The search query (game name or app ID)
    
    Returns:
        SteamSearchResponse: JSON object containing success status, list of matches, and count
    """
    if not steam_helper:
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': 'SteamHelper not initialized. Go to Settings > Credentials and check that credentials are correct.',
                'matches': [],
                'count': 0,
                'limit': 50
            }
        )
    
    try:
        logger.info(f"Searching Steam for: {query}")
        max_matches_limit = 50  # Limit results to 50 for performance
        matches = steam_helper.search_for_steam_game(query.strip(), max_matches_limit=max_matches_limit)
        
        logger.info(f"Found {len(matches)} matches for query: {query}")
        
        return {
            'success': True,
            'matches': matches,
            'count': len(matches),
            'limit': max_matches_limit,
            'error': None
        }
    except Exception as e:
        logger.error(f"Error searching Steam games: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': str(e),
                'matches': [],
                'count': 0,
                'limit': 50
            }
        )

@router.get('/app/{app_id}', response_model=steam_schemas.SteamAppInfoResponse)
async def get_steam_app_info(app_id: str, steam_helper: SteamHelper = Depends(get_steam_helper)):
    """
    API endpoint to get detailed information about a Steam app.
    
    Args:
        app_id: The Steam app ID
    
    Returns:
        SteamAppInfoResponse: JSON object containing app details
    """
    if not steam_helper:
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': 'SteamHelper not initialized. Go to Settings > Credentials and check that credentials are correct.',
                'app_info': None
            }
        )
    
    try:
        logger.info(f"Getting Steam app info for app_id: {app_id}")
        app_info = steam_helper.get_app_info(app_id)
        
        if app_info:
            logger.info(f"Successfully retrieved info for app_id: {app_id}")
            return {
                'success': True,
                'app_info': app_info,
                'error': None
            }
        else:
            logger.warning(f"No data available for app_id: {app_id}")
            return {
                'success': False,
                'app_info': None,
                'error': f'No data available for app ID {app_id}. Check if the Steam store page is available.'
            }
    except Exception as e:
        logger.error(f"Error getting Steam app info: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': str(e),
                'app_info': None
            }
        )