from pydantic import BaseModel
from typing import Optional

class GenieStartRequest(BaseModel):
    game_name: str
    content_type: Optional[str] = None

class GenieQueryRequest(BaseModel):
    conversation_id: str
    question: str

class GenieResponse(BaseModel):
    success: bool
    conversation_id: Optional[str] = None
    text_response: Optional[str] = None
    has_dataframe: bool = False
    dataframe_html: Optional[str] = None
    query_text: Optional[str] = None
    error: Optional[str] = None