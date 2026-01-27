from pydantic import BaseModel
from typing import List, Optional

class RedditSearchResponse(BaseModel):
    success: bool
    matches: List[str]
    count: int
    limit: int
    error: Optional[str] = None

class RedditSubredditInfoResponse(BaseModel):
    success: bool
    subreddit_info: Optional[dict] = None
    error: Optional[str] = None
