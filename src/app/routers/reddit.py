import logging
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from utils.reddit import RedditHelper
from dependencies import get_reddit_helper
from schemas import reddit as reddit_schemas

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reddit")

@router.get('/search', response_model=reddit_schemas.RedditSearchResponse)
async def search_reddit_subreddits(query: str = Query(..., min_length=1, description="Search query for Reddit subreddits"),
                                   reddit_helper: RedditHelper = Depends(get_reddit_helper)):
    """
    API endpoint to search for Reddit subreddits.
    
    Args:
        query: The search query (subreddit name or topic)
    
    Returns:
        RedditSearchResponse: JSON object containing success status, list of subreddit names, and count
    """
    if not reddit_helper:
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'matches': [],
                'count': 0,
                'limit': 0,
                'error': 'RedditHelper not initialized. Check Reddit API credentials.'
            }
        )
    
    try:
        logger.info(f"Searching Reddit for query: {query}")
        max_matches_limit = 50
        subreddit_names = reddit_helper.search_subreddits(query, limit=max_matches_limit)
        
        logger.info(f"Found {len(subreddit_names)} subreddits for query: {query}")
        return {
            'success': True,
            'matches': subreddit_names,
            'count': len(subreddit_names),
            'limit': max_matches_limit,
            'error': None
        }
    except Exception as e:
        logger.error(f"Error searching Reddit: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'matches': [],
                'count': 0,
                'limit': 0,
                'error': str(e)
            }
        )

@router.get('/subreddit/{subreddit_name}', response_model=reddit_schemas.RedditSubredditInfoResponse)
async def get_reddit_subreddit_info(subreddit_name: str, reddit_helper: RedditHelper = Depends(get_reddit_helper)):
    """
    API endpoint to get detailed information about a Reddit subreddit.
    
    Args:
        subreddit_name: The subreddit name (without r/)
    
    Returns:
        RedditSubredditInfoResponse: JSON object containing subreddit details
    """
    if not reddit_helper:
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': 'RedditHelper not initialized. Check Reddit API credentials.',
                'subreddit_info': None
            }
        )
    
    try:
        logger.info(f"Getting Reddit subreddit info for: {subreddit_name}")
        subreddit_info = reddit_helper.get_subreddit_info(subreddit_name)
        
        logger.info(f"Successfully retrieved info for subreddit: {subreddit_name}")
        return {
            'success': True,
            'subreddit_info': subreddit_info,
            'error': None
        }
    except Exception as e:
        logger.error(f"Error getting Reddit subreddit info: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': str(e),
                'subreddit_info': None
            }
        )