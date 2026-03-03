import logging
import os
from enum import Enum

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from utils.reddit import RedditHelper
from utils.databricks import DatabricksClient
from dependencies import (
    get_reddit_helper,
    set_reddit_helper,
    get_databricks_client,
    get_secret_scope,
    get_reddit_client_id_secret_key,
    get_reddit_client_secret_secret_key,
    get_reddit_user_agent_secret_key,
)
from schemas import reddit as reddit_schemas

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reddit")


class RedditCredentialsTestStatus(Enum):
    """Result of testing Reddit API credentials."""
    VALID = 1
    INVALID = 2
    NOT_CONFIGURED = 3


def resolve_empty_values(value: str | None, env_var: str) -> str:
    """
    Use value if header was sent (including explicit empty), else env var.
    When the client sends a header with empty value, treat as explicit empty so blank form fields are caught.
    """
    if value is not None and value != "":
        return value
    return os.environ.get(env_var)


def test_reddit_credentials(
    client_id: str | None = None,
    client_secret: str | None = None,
    user_agent: str | None = None,
) -> tuple[RedditCredentialsTestStatus, RedditHelper | None]:
    """
    Test Reddit credentials by instantiating RedditHelper.
    For any None/empty argument, uses the corresponding env var (REDDIT_CLIENT_ID, etc.).

    Returns:
        Tuple of (status, helper): VALID with helper, or INVALID/NOT_CONFIGURED with None.
    """
    client_id = resolve_empty_values(client_id, "REDDIT_CLIENT_ID")
    client_secret = resolve_empty_values(client_secret, "REDDIT_CLIENT_SECRET")
    user_agent = resolve_empty_values(user_agent, "REDDIT_USER_AGENT")
    if not client_id or client_id == "" or not client_secret or client_secret == "" or not user_agent or user_agent == "":
        return (RedditCredentialsTestStatus.NOT_CONFIGURED, None)
    try:
        helper = RedditHelper(client_id=client_id, client_secret=client_secret, user_agent=user_agent)
        return (RedditCredentialsTestStatus.VALID, helper)
    except Exception as e:
        return (RedditCredentialsTestStatus.INVALID, None)


@router.get('/test-credentials')
async def test_reddit_credentials_endpoint(
    client_id: str | None = Header(None, description="Reddit Client ID; if omitted, uses REDDIT_CLIENT_ID env var"),
    client_secret: str | None = Header(None, description="Reddit Client Secret; if omitted, uses REDDIT_CLIENT_SECRET env var"),
    reddit_user_agent: str | None = Header(None, description="Reddit User Agent; if omitted, uses REDDIT_USER_AGENT env var"),
    databricks_client: DatabricksClient | None = Depends(get_databricks_client),
    secret_scope: str | None = Depends(get_secret_scope),
    reddit_client_id_secret_key: str | None = Depends(get_reddit_client_id_secret_key),
    reddit_client_secret_secret_key: str | None = Depends(get_reddit_client_secret_secret_key),
    reddit_user_agent_secret_key: str | None = Depends(get_reddit_user_agent_secret_key),
):
    """
    Test Reddit credentials. Returns status: valid, invalid, or not_configured.
    On valid, updates the app's RedditHelper, env vars, and (if available) Databricks secrets.
    """
    result, reddit_helper = test_reddit_credentials(
        client_id=client_id, client_secret=client_secret, user_agent=reddit_user_agent
    )
    if result == RedditCredentialsTestStatus.VALID and reddit_helper is not None:
        os.environ["REDDIT_CLIENT_ID"] = reddit_helper.client_id
        os.environ["REDDIT_CLIENT_SECRET"] = reddit_helper.client_secret
        os.environ["REDDIT_USER_AGENT"] = reddit_helper.user_agent
        set_reddit_helper(reddit_helper)
        if databricks_client is not None and secret_scope:
            for key_name, value in [
                (reddit_client_id_secret_key, client_id),
                (reddit_client_secret_secret_key, client_secret),
                (reddit_user_agent_secret_key, reddit_user_agent),
            ]:
                if key_name and value:
                    try:
                        databricks_client.put_secret(scope=secret_scope, key=key_name, string_value=value)
                        logger.info("Updated Databricks secret %s/%s", secret_scope, key_name)
                    except Exception as e:
                        logger.warning("Could not update Databricks secret %s: %s", key_name, e)
        logger.info("Updated app RedditHelper with tested/valid credentials")
    return {"status": result.name.lower()}


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
                'error': 'RedditHelper not initialized. Go to Settings > Credentials and check that credentials are correct.',
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
                'error': 'RedditHelper not initialized. Go to Settings > Credentials and check that credentials are correct.',
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