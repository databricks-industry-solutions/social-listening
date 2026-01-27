import logging
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from utils.steam import SteamHelper
from dependencies import get_steam_helper
from schemas import steam as steam_schemas

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/steam")

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
                'error': 'SteamHelper not initialized. See logs for more details.',
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
                'error': 'SteamHelper not initialized.',
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