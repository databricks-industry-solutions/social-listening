from pydantic import BaseModel
from typing import List, Optional

class PersonasResponse(BaseModel):
    success: bool
    personas: List[str]
    error: Optional[str] = None

class ReportResponse(BaseModel):
    success: bool
    subject: Optional[str] = None
    summary_contents: Optional[str] = None
    expanded_contents: Optional[str] = None
    error: Optional[str] = None
