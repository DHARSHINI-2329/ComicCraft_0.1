"""Panel Pydantic schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DialogueLine(BaseModel):
    character: str
    text: str


class PanelOutline(BaseModel):
    """Panel data as returned by the AI story outline."""
    panel_number: int
    title: str
    scene_description: str
    narration: str
    dialogue: list[DialogueLine] = []
    image_prompt: str


class PanelResponse(BaseModel):
    """Panel data returned to the frontend."""
    id: int
    comic_id: str
    panel_number: int
    title: str
    scene_description: str
    narration: str
    dialogue: list[DialogueLine] = []
    image_prompt: str
    image_path: Optional[str] = None
    image_url: Optional[str] = None
    generation_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
