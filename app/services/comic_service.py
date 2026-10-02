"""Comic service: CRUD operations and business logic for comics."""
import json
import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.models.comic import Comic
from app.models.panel import Panel
from app.models.generation_job import GenerationJob
from app.schemas.panel import PanelResponse, DialogueLine
from app.schemas.comic import ComicResponse, ComicListItem
from app.utils.file_utils import new_id, image_url_from_path

logger = logging.getLogger(__name__)


def _panel_to_response(panel: Panel) -> PanelResponse:
    """Convert a Panel DB model to a PanelResponse schema."""
    dialogue_list: list[DialogueLine] = []
    if panel.dialogue:
        try:
            raw = json.loads(panel.dialogue)
            for item in raw:
                if isinstance(item, dict):
                    dialogue_list.append(DialogueLine(
                        character=item.get("character", ""),
                        text=item.get("text", ""),
                    ))
        except (json.JSONDecodeError, TypeError):
            pass

    return PanelResponse(
        id=panel.id,
        comic_id=panel.comic_id,
        panel_number=panel.panel_number,
        title=panel.title,
        scene_description=panel.scene_description,
        narration=panel.narration,
        dialogue=dialogue_list,
        image_prompt=panel.image_prompt,
        image_path=panel.image_path,
        image_url=image_url_from_path(panel.image_path),
        generation_status=panel.generation_status,
        created_at=panel.created_at,
        updated_at=panel.updated_at,
    )


class ComicService:
    """High-level comic management: creation, retrieval, deletion, favorites."""

    def create_comic_record(
        self,
        db: Session,
        user_id: int,
        story_prompt: str,
        character_name: str,
        character_description: Optional[str],
        setting: str,
        tone: str,
        art_style: str,
        chapter_number: int = 1,
        parent_comic_id: Optional[str] = None,
    ) -> Comic:
        """Create a new Comic record and return it."""
        comic_id = new_id()
        title = f"{character_name}'s Adventure"
        comic = Comic(
            id=comic_id,
            user_id=user_id,
            title=title,
            story_prompt=story_prompt,
            character_name=character_name,
            character_description=character_description,
            setting=setting,
            tone=tone,
            art_style=art_style,
            chapter_number=chapter_number,
            parent_comic_id=parent_comic_id,
        )
        db.add(comic)
        db.commit()
        db.refresh(comic)
        return comic

    def create_job(
        self,
        db: Session,
        comic_id: str,
        job_type: str,
        panel_number: Optional[int] = None,
    ) -> GenerationJob:
        """Create and persist a generation job."""
        job = GenerationJob(
            id=new_id(),
            comic_id=comic_id,
            job_type=job_type,
            status="PENDING",
            panel_number=panel_number,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def get_comic(self, db: Session, comic_id: str, user_id: int) -> Optional[Comic]:
        """Get a comic if it belongs to the user."""
        return (
            db.query(Comic)
            .filter(Comic.id == comic_id, Comic.user_id == user_id)
            .first()
        )

    def get_panel(self, db: Session, comic_id: str, panel_number: int) -> Optional[Panel]:
        """Get a panel by comic and number."""
        return (
            db.query(Panel)
            .filter(Panel.comic_id == comic_id, Panel.panel_number == panel_number)
            .first()
        )

    def get_job(self, db: Session, job_id: str) -> Optional[GenerationJob]:
        return db.query(GenerationJob).filter(GenerationJob.id == job_id).first()

    def list_user_comics(
        self,
        db: Session,
        user_id: int,
        favorites_only: bool = False,
        search: Optional[str] = None,
    ) -> list[Comic]:
        q = db.query(Comic).filter(Comic.user_id == user_id)
        if favorites_only:
            q = q.filter(Comic.is_favorite == True)
        if search:
            q = q.filter(
                Comic.title.ilike(f"%{search}%") |
                Comic.character_name.ilike(f"%{search}%") |
                Comic.setting.ilike(f"%{search}%")
            )
        return q.order_by(Comic.created_at.desc()).all()

    def toggle_favorite(self, db: Session, comic: Comic) -> Comic:
        comic.is_favorite = not comic.is_favorite
        db.commit()
        db.refresh(comic)
        return comic

    def delete_comic(self, db: Session, comic: Comic) -> None:
        db.delete(comic)
        db.commit()

    def comic_to_response(self, comic: Comic) -> ComicResponse:
        """Convert a Comic DB model to ComicResponse."""
        return ComicResponse(
            id=comic.id,
            user_id=comic.user_id,
            title=comic.title,
            story_prompt=comic.story_prompt,
            character_name=comic.character_name,
            character_description=comic.character_description,
            setting=comic.setting,
            tone=comic.tone,
            art_style=comic.art_style,
            summary=comic.summary,
            chapter_number=comic.chapter_number,
            parent_comic_id=comic.parent_comic_id,
            is_favorite=comic.is_favorite,
            thumbnail_url=image_url_from_path(comic.thumbnail_path),
            panels=[_panel_to_response(p) for p in sorted(comic.panels, key=lambda x: x.panel_number)],
            created_at=comic.created_at,
            updated_at=comic.updated_at,
        )

    def panel_to_response(self, panel: Panel) -> PanelResponse:
        return _panel_to_response(panel)
