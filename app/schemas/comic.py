"""Comic Pydantic schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator
from app.schemas.panel import PanelResponse


VALID_SETTINGS = [
    "Forest", "School", "City", "Space", "Fantasy Kingdom",
    "Beach", "Laboratory", "Custom", "Enchanted Forest",
]
VALID_TONES = [
    "Light-hearted", "Dramatic", "Funny", "Adventure",
    "Emotional", "Mysterious", "Poetic", "Dark",
]
VALID_STYLES = [
    "Anime", "Comic Book", "Cartoon", "Pixel Art",
    "Fantasy", "Watercolor", "Cinematic", "Realistic",
]


class ComicCreateRequest(BaseModel):
    story_prompt: str
    character_name: str
    character_description: Optional[str] = None
    setting: str
    tone: str
    art_style: str

    @field_validator("story_prompt")
    @classmethod
    def prompt_not_empty(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Story prompt must be at least 10 characters")
        if len(v) > 2000:
            raise ValueError("Story prompt must be under 2000 characters")
        return v

    @field_validator("character_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Character name is required")
        return v


class CharacterProfileSchema(BaseModel):
    name: str
    appearance: str = ""
    personality: str = ""
    clothing: str = ""
    visual_identifiers: list[str] = []
    species: str = ""
    age: str = ""


class ComicOutlineSchema(BaseModel):
    """The full structured AI outline for a comic."""
    title: str
    summary: str
    character_profile: CharacterProfileSchema
    panels: list[dict]  # validated downstream


class ComicResponse(BaseModel):
    id: str
    user_id: int
    title: str
    story_prompt: str
    character_name: str
    character_description: Optional[str] = None
    setting: str
    tone: str
    art_style: str
    summary: Optional[str] = None
    chapter_number: int
    parent_comic_id: Optional[str] = None
    is_favorite: bool
    thumbnail_url: Optional[str] = None
    panels: list[PanelResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ComicListItem(BaseModel):
    id: str
    title: str
    character_name: str
    setting: str
    tone: str
    art_style: str
    chapter_number: int
    is_favorite: bool
    thumbnail_url: Optional[str] = None
    panel_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerateComicResponse(BaseModel):
    success: bool
    comic_id: str
    title: str
    status: str
    job_id: Optional[str] = None
    message: Optional[str] = None
