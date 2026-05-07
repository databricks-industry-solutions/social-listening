from pydantic import BaseModel
from typing import Optional

class DashboardUrlResponse(BaseModel):
    success: bool
    dashboard_url: str
    error: Optional[str] = None