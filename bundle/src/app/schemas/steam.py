from pydantic import BaseModel
from typing import List, Optional

class SteamSearchResponse(BaseModel):
    success: bool
    matches: List[dict]
    count: int
    limit: int
    error: Optional[str] = None

class SteamAppInfoResponse(BaseModel):
    success: bool
    app_info: Optional[dict] = None
    error: Optional[str] = None
