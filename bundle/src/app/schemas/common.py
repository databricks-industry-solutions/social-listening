from pydantic import BaseModel
from typing import List, Optional
# Response models
class GameEntry(BaseModel):
    game_name: str
    content_type: str

class GamesResponse(BaseModel):
    success: bool
    games: List[GameEntry]
    database_info: Optional[str] = None
    error: Optional[str] = None

class AddGameResponse(BaseModel):
    success: bool
    run_id: Optional[int] = None
    run_page_url: Optional[str] = None
    error: Optional[str] = None