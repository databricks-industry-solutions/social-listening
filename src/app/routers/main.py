import logging
from pathlib import Path
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from utils.rendering import get_app_config, get_sidebar_config, render_sidebar_links
from dependencies import get_template_path, get_data_loader
from schemas import common as common_schemas
from utils.data import DataLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get('/', response_class=HTMLResponse)
async def index(template_path: Path = Depends(get_template_path)):
    """Serve the main HTML page with injected configuration."""
    try:
        html_content = template_path.read_text(encoding='utf-8')
        
        # Get configuration and render links
        config = get_sidebar_config()
        sidebar_links_html = render_sidebar_links(config)
        
        # Replace the placeholder in HTML with rendered links
        html_content = html_content.replace(
            '<!-- SIDEBAR_LINKS_PLACEHOLDER -->',
            sidebar_links_html
        )
        
        return html_content
    except Exception as e:
        logger.error(f"Error loading HTML template: {e}")
        return HTMLResponse(
            content="<h1>Error loading page</h1><p>Unable to load the HTML template.</p>",
            status_code=500
        )

@router.get('/api/config')
async def get_config():
    """
    API endpoint to get application configuration including sidebar links.
    
    Returns:
        JSON object containing configuration data
    """
    return get_app_config()

@router.get('/api/user-token')
async def get_user_token(data_loader: DataLoader = Depends(get_data_loader)):
    """
    API endpoint to get the user access token for embedded dashboards.
    
    Returns:
        JSON object containing the user token
    """
    try:
        if data_loader:
            token = data_loader.get_user_token()
            if token:
                return {'success': True, 'token': token}
            else:
                return JSONResponse(
                    status_code=401,
                    content={'success': False, 'error': 'No access token found in request headers'}
                )
        else:
            return JSONResponse(
                status_code=500,
                content={'success': False, 'error': 'DataLoader not initialized'}
            )
    except Exception as e:
        logger.error(f"Error getting user token: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={'success': False, 'error': str(e)}
        )

@router.get('/api/games', response_model=common_schemas.GamesResponse)
async def get_games(data_loader: DataLoader = Depends(get_data_loader)):
    """
    API endpoint to get the list of games and their content types from Databricks.
    
    Returns:
        GamesResponse: JSON object containing success status, list of games with content types, and database info
    """
    if not data_loader:
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': 'DataLoader not initialized. Check Databricks configuration.',
                'games': [],
                'database_info': None
            }
        )
    
    try:
        logger.info("Fetching game names and content types from Databricks...")
        games_data = data_loader.get_game_names()
        if games_data is None:
            return JSONResponse(
                status_code=500,
                content={
                    'success': False,
                    'error': 'Failed to fetch game names from Databricks; see logs for more details.',
                    'games': [],
                    'database_info': f"{data_loader.catalog_name}.{data_loader.schema_name}.{data_loader.game_reviews_table_name}"
                }
            )
        
        # Sort games alphabetically by game_name
        games_data.sort(key=lambda x: x['game_name'])
        
        logger.info(f"Successfully retrieved {len(games_data)} game entries")
        
        return {
            'success': True,
            'games': games_data,
            'database_info': f"{data_loader.catalog_name}.{data_loader.schema_name}.{data_loader.game_reviews_table_name}",
            'error': None
        }
    except Exception as e:
        logger.error(f"Error fetching games: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': str(e),
                'games': [],
                'database_info': None
            }
        )