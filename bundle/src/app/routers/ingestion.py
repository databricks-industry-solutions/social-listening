import logging
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from utils.databricks import DatabricksClient
from dependencies import get_databricks_client
from schemas import common as common_schemas

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingestion")

@router.get('/check-table-exists')
async def check_table_exists(table_path: str, databricks_client: DatabricksClient = Depends(get_databricks_client)):
    """
    API endpoint to check if a table exists in the Databricks workspace.
    
    Args:
        table_path: Full table path in format catalog.schema.table
    
    Returns:
        JSON object containing success status and exists boolean
    """
    if not databricks_client:
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': 'DatabricksClient not initialized.',
                'exists': False
            }
        )
    
    try:
        catalog, schema, table = table_path.split('.')
        exists = databricks_client.check_table_exists(catalog, schema, table)
        return {
            'success': True,
            'exists': exists,
            'table_path': table_path,
            'error': None
        }
    except Exception as e:
        logger.error(f"Error checking table existence: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': str(e),
                'exists': False
            }
        )

@router.get('/check-generic-table')
async def check_generic_table(table_path: str, databricks_client: DatabricksClient = Depends(get_databricks_client)):
    """
    API endpoint to check if a given generic table is in the correct format for ingestion.
    
    Args:
        table_path: Full table path in format catalog.schema.table
    
    Returns:
        JSON object containing success status and is_valid boolean
    """
    if not databricks_client:
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': 'DatabricksClient not initialized.',
                'is_valid': False
            }
        )
    try:
        catalog, schema, table = table_path.split('.')
        is_valid = databricks_client.check_generic_table(catalog, schema, table)
        return {
            'success': True,
            'is_valid': is_valid,
            'table_path': table_path,
            'error': None
        }
    except Exception as e:
        logger.error(f"Error checking generic table: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': str(e),
                'is_valid': False
            }
        )

@router.get('/generic-table-format')
async def get_generic_table_format(databricks_client: DatabricksClient = Depends(get_databricks_client)):
    """
    API endpoint to get the required format for generic table ingestion.
    
    Returns:
        JSON object containing the required column format
    """
    if not databricks_client:
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': 'DatabricksClient not initialized.',
                'format': []
            }
        )
    try:
        required_format = databricks_client.get_generic_table_required_format()
        return {
            'success': True,
            'format': required_format,
            'error': None
        }
    except Exception as e:
        logger.error(f"Error getting generic table format: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': str(e),
                'format': []
            }
        )

@router.post('/run-job', response_model=common_schemas.AddGameResponse)
async def run_ingestion_job(source_content_id: str, content_type: str, game_name: str, update_type: str="NEW_GAME",
                            databricks_client: DatabricksClient = Depends(get_databricks_client)):
    """
    API endpoint to trigger an ingestion job for a content source (e.g. Steam, Google Play, Reddit).
    The arguments match the parameters of the ingestion job; view the job page for more details.

    Args:
        source_content_id: Source Content ID (e.g. Steam app ID, Google Play app ID, Reddit subreddit name)
        content_type: Content type (e.g. Steam Review, Google Play Review, Reddit Comment)
        game_name: Name of the game
        update_type: Update type (e.g. "NEW_GAME", "REFRESH")
    
    Returns:
        AddGameResponse: JSON object containing success status, run_id, and run_page_url.
        The run_page_url is a link to the job run page in the Databricks workspace.
    """
    if not databricks_client:
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': 'DatabricksClient not initialized.',
                'run_id': None,
                'run_page_url': None
            }
        )
    
    try:
        logger.info(f"Adding {content_type} game: {game_name} (Source Content ID: {source_content_id}), Update Type: {update_type}")
        
        # Call DatabricksClient to run the ingestion job
        job_run_info = databricks_client.run_ingestion_job(
            source_content_id=source_content_id,
            content_type=content_type,
            game_name=game_name,
            update_type=update_type
        )
        
        logger.info(f"Job run submission info: {job_run_info}")
        
        return {
            'success': True,
            'run_id': job_run_info['run_id'],
            'run_page_url': job_run_info['run_page_url'],
            'error': None
        }
    except Exception as e:
        logger.error(f"Error adding Steam game: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': str(e),
                'run_id': None,
                'run_page_url': None
            }
        )
