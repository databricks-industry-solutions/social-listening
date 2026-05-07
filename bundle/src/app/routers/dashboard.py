import logging
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from schemas import dashboard as dashboard_schemas
from utils.report_utils import str_to_url_encoding
from dependencies import get_dashboard_url_info

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get('/api/dashboard-url', response_model=dashboard_schemas.DashboardUrlResponse)
async def get_dashboard_url(game_name: str = Query(None, description="The name of the game to filter by"),
                             dashboard_url_info: dict = Depends(get_dashboard_url_info)):
    """
    Get the dashboard URL, optionally filtered by game name.
    If game_name is provided, the URL will include filter parameters.
    """
    try:
        if game_name:
            # Encode the game name using double URL encoding
            encoded_game_name = str_to_url_encoding(game_name)
            
            # Construct the filtered dashboard URL
            filtered_url = (
                f"{dashboard_url_info['base']}"
                f"{dashboard_url_info['game_filter_suffix']}{encoded_game_name}"
                f"{dashboard_url_info['category_page_game_filter_suffix']}{encoded_game_name}"
            )
            
            logger.info(f"Generated dashboard URL for game: {game_name}")
            return {
                'success': True,
                'dashboard_url': filtered_url,
                'error': None
            }
        else:
            # Return base URL without filters
            return {
                'success': True,
                'dashboard_url': dashboard_url_info['base'],
                'error': None
            }
    except Exception as e:
        logger.error(f"Error generating dashboard URL: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'dashboard_url': dashboard_url_info['base'],
                'error': str(e)
            }
        )