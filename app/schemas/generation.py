"""Generation job Pydantic schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class JobStatusResponse(BaseModel):
    id: str
    comic_id: str
    job_type: str
    status: str
    current_step: Optional[str] = None
    error_message: Optional[str] = None
    panel_number: Optional[int] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
