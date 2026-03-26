import logging
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from utils.data import DataLoader
from utils.report_utils import split_report_contents
from dependencies import get_data_loader
from schemas import report as report_schemas
import markdown

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get('/api/personas', response_model=report_schemas.PersonasResponse)
async def get_personas(game_name: str = Query(..., description="The name of the game"), data_loader: DataLoader = Depends(get_data_loader)):
    """
    API endpoint to get the list of personas for a given game.
    
    Args:
        game_name: The name of the game
    
    Returns:
        PersonasResponse: JSON object containing the list of personas
    """
    if not data_loader:
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'personas': [],
                'error': 'DataLoader not initialized.'
            }
        )
    
    try:
        logger.info(f"Getting personas for game: {game_name}")
        personas = data_loader.get_persona_names(game_name=game_name)
        
        logger.info(f"Found {len(personas)} personas for game: {game_name}")
        
        return {
            'success': True,
            'personas': personas,
            'error': None
        }
    except Exception as e:
        logger.error(f"Error getting personas: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'personas': [],
                'error': str(e)
            }
        )

@router.get('/api/report', response_model=report_schemas.ReportResponse)
async def get_report(
    game_name: str = Query(..., description="The name of the game"),
    persona: str = Query(..., description="The persona name"),
    data_loader: DataLoader = Depends(get_data_loader)
):
    """
    API endpoint to get the report for a given game and persona.
    
    Args:
        game_name: The name of the game
        persona: The persona name
    
    Returns:
        ReportResponse: JSON object containing the report contents
    """
    if not data_loader:
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'report_contents': None,
                'error': 'DataLoader not initialized.'
            }
        )
    
    try:
        logger.info(f"Getting report for game: {game_name}, persona: {persona}")
        data = data_loader.load_game_review_reports(game_name=game_name)
        
        # Filter by game and persona
        game_data = data[data["game_name"] == game_name]
        persona_data = game_data[game_data["persona"] == persona]
        
        if persona_data.empty:
            return {
                'success': False,
                'subject': None,
                'summary_contents': None,
                'expanded_contents': None,
                'error': f'No report found for game "{game_name}" with persona "{persona}"'
            }
        
        report_contents = persona_data["report_contents"].values[0]
        
        # Split the report into subject, summary and expanded sections
        subject_contents, summary_contents, expanded_contents = split_report_contents(report_contents)
        
        # Convert markdown to HTML
        subject_html = markdown.markdown(subject_contents) if subject_contents else None
        summary_html = markdown.markdown(summary_contents)
        expanded_html = markdown.markdown(expanded_contents) if expanded_contents else None
        
        logger.info(f"Successfully retrieved report for game: {game_name}, persona: {persona}")
        
        return {
            'success': True,
            'subject': subject_html,
            'summary_contents': summary_html,
            'expanded_contents': expanded_html,
            'error': None
        }
    except Exception as e:
        logger.error(f"Error getting report: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'subject': None,
                'summary_contents': None,
                'expanded_contents': None,
                'error': str(e)
            }
        )