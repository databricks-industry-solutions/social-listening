import logging
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from utils.genie_room import genie_query, start_new_conversation, refresh_genie_token
from schemas import genie as genie_schemas

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/genie")

@router.post('/refresh-token')
async def refresh_token():
    """
    Refresh the Genie token.
    
    Returns:
        JSON object indicating success
    """
    try:
        logger.info("Refreshing Genie token...")
        refresh_genie_token()
        logger.info("Genie token refreshed successfully")
        return {
            'success': True,
            'error': None
        }
    except Exception as e:
        logger.error(f"Error refreshing Genie token: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': str(e)
            }
        )

@router.post('/start', response_model=genie_schemas.GenieResponse)
async def start_genie_conversation(request: genie_schemas.GenieStartRequest):
    """
    Start a new Genie conversation for a specific game.
    
    Args:
        request: Contains game_name
    
    Returns:
        GenieResponse with conversation_id and initial response
    """
    try:
        game_name = request.game_name
        logger.info(f"Starting new Genie conversation for game: {game_name}")
        
        # Create starter prompt to seed the conversation
        starter_prompt = (
            f"Ignore the previous games we have talked about in the past. "
            f"The game I'm interested in now is '{game_name}' and my subsequent questions "
            f"that don't specify a game name will be referring to {game_name} until we start talking about a different game."
        )
        
        conversation_id, text_response, df_response, query_text = start_new_conversation(starter_prompt)
        
        logger.info(f"Started conversation with ID: {conversation_id}")
        
        # Convert DataFrame to HTML if present
        dataframe_html = None
        if df_response is not None:
            dataframe_html = df_response.to_html(classes='genie-dataframe', index=False)
        
        return {
            'success': True,
            'conversation_id': conversation_id,
            'text_response': text_response,
            'has_dataframe': df_response is not None,
            'dataframe_html': dataframe_html,
            'query_text': query_text,
            'error': None
        }
    except Exception as e:
        logger.error(f"Error starting Genie conversation: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'conversation_id': None,
                'text_response': None,
                'has_dataframe': False,
                'dataframe_html': None,
                'query_text': None,
                'error': str(e)
            }
        )

@router.post('/query', response_model=genie_schemas.GenieResponse)
async def query_genie(request: genie_schemas.GenieQueryRequest):
    """
    Send a question to Genie in an existing conversation.
    
    Args:
        request: Contains conversation_id and question
    
    Returns:
        GenieResponse with text response and optional dataframe
    """
    try:
        conversation_id = request.conversation_id
        question = request.question
        
        logger.info(f"Querying Genie (conversation: {conversation_id}): {question}")
        
        # Query Genie
        conversation_id, text_response, df_response, query_text = genie_query(question, conversation_id)
        
        # Convert DataFrame to HTML if present
        dataframe_html = None
        if df_response is not None:
            dataframe_html = df_response.to_html(classes='genie-dataframe', index=False)
        
        return {
            'success': True,
            'conversation_id': conversation_id,
            'text_response': text_response,
            'has_dataframe': df_response is not None,
            'dataframe_html': dataframe_html,
            'query_text': query_text,
            'error': None
        }
    except Exception as e:
        logger.error(f"Error querying Genie: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'conversation_id': conversation_id if 'conversation_id' in locals() else None,
                'text_response': None,
                'has_dataframe': False,
                'dataframe_html': None,
                'query_text': None,
                'error': str(e)
            }
        )