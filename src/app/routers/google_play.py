import logging
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from utils.google_play import GooglePlayHelper
from dependencies import get_google_play_helper
from schemas import google_play as google_play_schemas

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/google-play")

@router.get('/search', response_model=google_play_schemas.GooglePlaySearchResponse)
async def search_google_play_games(query: str = Query(..., min_length=1, description="Search query for Google Play games"),
                                   google_play_helper: GooglePlayHelper = Depends(get_google_play_helper)):
    """
    API endpoint to search for Google Play games.
    
    Args:
        query: The search query (game name or other string)
    
    Returns:
        GooglePlaySearchResponse: JSON object containing success status, list of matches, and count
    """
    if not google_play_helper:
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': 'GooglePlayHelper not initialized. Check Google Play API credentials and that the Databricks Secret(s) have been added to the app.',
                'matches': [],
                'count': 0,
                'limit': 30
            }
        )
    
    try:
        logger.info(f"Searching Google Play for: {query}")
        matches = google_play_helper.search_for_google_play_app(query.strip())
        
        logger.info(f"Found {len(matches)} matches for query: {query}")
        logger.info(f"First 5 matches: {matches[:5]}")

        return {
            'success': True,
            'matches': matches,
            'count': len(matches),
            'limit': 30,
            'error': None
        }
    except Exception as e:
        logger.error(f"Error searching Google Play: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': str(e),
                'matches': [],
                'count': 0,
                'limit': 30
            }
        )

@router.get('/app/{app_id}', response_model=google_play_schemas.GooglePlayAppInfoResponse)
async def get_google_play_app_info(app_id: str, google_play_helper: GooglePlayHelper = Depends(get_google_play_helper)):
    """
    API endpoint to get detailed information about a Google Play app.
    
    Args:
        app_id: The Google Play app ID
    
    Returns:
        GooglePlayAppInfoResponse: JSON object containing app details
    """
    if not google_play_helper:
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': 'GooglePlayHelper not initialized. Check Google Play API credentials and that the Databricks Secret(s) have been added to the app.',
                'app_info': None
            }
        )
    
    try:
        logger.info(f"Getting Google Play app info for app_id: {app_id}")
        app_info_raw = google_play_helper.get_app_info(app_id)
        
        if app_info_raw:
            # Extract and format the relevant fields
            default_value = 'Unavailable (see store page above)'
            app_info = {
                'headerImage': app_info_raw.get('headerImage', default_value),
                'title': app_info_raw.get('title', default_value),
                'appId': app_info_raw.get('appId', app_id),
                'genre': app_info_raw.get('genre', default_value),
                'released': app_info_raw.get('released', default_value),
                'reviews': app_info_raw.get('reviews', default_value),
                'score': app_info_raw.get('score', default_value),
                'store_url': google_play_helper.get_store_page_url(app_id)
            }
            # Extra catch for None entries
            if app_info.get('headerImage') is None:
                app_info['headerImage'] = default_value
            if app_info.get('title') is None:
                app_info['title'] = default_value
            if app_info.get('appId') is None:
                app_info['appId'] = app_id
            if app_info.get('genre') is None:
                app_info['genre'] = default_value
            if app_info.get('released') is None:
                app_info['released'] = default_value
            if app_info.get('reviews') is None:
                app_info['reviews'] = default_value
            if app_info.get('score') is None:
                app_info['score'] = default_value
            
            logger.info(f"Successfully retrieved info for app_id: {app_id}: {app_info}")
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
                'error': f'No data available for app ID {app_id}. Check if the Google Play store page is available.'
            }
    except Exception as e:
        logger.error(f"Error getting Google Play app info: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': str(e),
                'app_info': None
            }
        )