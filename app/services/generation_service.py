"""Generation service: orchestrates the full comic generation pipeline."""
import json
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.comic import Comic
from app.models.panel import Panel
from app.models.generation_job import GenerationJob
from app.services.story_service import StoryService
from app.services.character_service import CharacterService
from app.services.image_service import ImageService
from app.utils.file_utils import new_id

logger = logging.getLogger(__name__)

story_svc = StoryService()
char_svc = CharacterService()
image_svc = ImageService()


def _update_job(db: Session, job: GenerationJob, status: str, step: str | None = None, error: str | None = None):
    """Update a generation job's status."""
    job.status = status
    job.current_step = step
    if error:
        job.error_message = error
    if status == "RUNNING" and not job.started_at:
        job.started_at = datetime.now(timezone.utc)
    if status in ("COMPLETED", "FAILED"):
        job.completed_at = datetime.now(timezone.utc)
    db.commit()


def run_full_generation(db: Session, comic: Comic, job: GenerationJob) -> None:
    """Execute the complete comic generation pipeline synchronously.

    Steps:
      1. Generate story outline (Gemini)
      2. Persist character profile
      3. Create panel records
      4. Generate panel images (one per panel)
      5. Mark job complete
    """
    try:
        _update_job(db, job, "RUNNING", "Planning the story...")

        # ── Step 1: Story outline ─────────────────────────────────────────
        outline = story_svc.generate_outline(
            story_prompt=comic.story_prompt,
            character_name=comic.character_name,
            setting=comic.setting,
            tone=comic.tone,
            art_style=comic.art_style,
            character_description=comic.character_description,
        )

        comic.title = outline.get("title", comic.title)
        comic.summary = outline.get("summary", "")
        db.commit()

        _update_job(db, job, "RUNNING", "Creating character profile...")

        # ── Step 2: Character profile ─────────────────────────────────────
        char_profile_data = outline.get("character_profile", {})
        character = char_svc.create_from_profile(db, comic.id, char_profile_data)
        char_profile = char_svc.get_profile_dict(character)

        _update_job(db, job, "RUNNING", "Writing panel narrations...")

        # ── Step 3: Create panel records ──────────────────────────────────
        panels_data = outline.get("panels", [])
        db_panels: list[Panel] = []
        for p_data in panels_data:
            dialogue = p_data.get("dialogue", [])
            panel = Panel(
                comic_id=comic.id,
                panel_number=int(p_data.get("panel_number", 1)),
                title=str(p_data.get("title", "")),
                scene_description=str(p_data.get("scene_description", "")),
                narration=str(p_data.get("narration", "")),
                dialogue=json.dumps(dialogue),
                image_prompt=str(p_data.get("image_prompt", "")),
                generation_status="PENDING",
            )
            db.add(panel)
            db_panels.append(panel)
        db.commit()

        _update_job(db, job, "RUNNING", "Generating illustrations...")

        # ── Step 4: Generate images ───────────────────────────────────────
        results = image_svc.generate_all_panel_images(
            db=db,
            panels=db_panels,
            character_profile=char_profile,
            art_style=comic.art_style,
        )

        # Set thumbnail from panel 1
        if db_panels and db_panels[0].image_path:
            comic.thumbnail_path = db_panels[0].image_path
            db.commit()

        failed = [p for p, ok in results.items() if not ok]
        if failed:
            logger.warning(f"Comic {comic.id}: image generation failed for panels {failed}")

        _update_job(db, job, "COMPLETED", "Comic ready!")
        logger.info(f"Comic {comic.id} generation complete.")

    except Exception as e:
        logger.exception(f"Comic generation failed for {comic.id}: {e}")
        _update_job(db, job, "FAILED", error=str(e))


def run_panel_regeneration(
    db: Session,
    comic: Comic,
    panel: Panel,
    job: GenerationJob,
) -> None:
    """Regenerate a single panel's story content and image."""
    try:
        _update_job(db, job, "RUNNING", f"Regenerating panel {panel.panel_number}...")

        char_profile = char_svc.get_profile_dict(comic.character) if comic.character else {}

        # Regenerate story content
        panel_data = story_svc.regenerate_panel(
            comic_title=comic.title,
            panel_number=panel.panel_number,
            character_profile=char_profile,
            story_summary=comic.summary or "",
            original_scene_description=panel.scene_description,
            setting=comic.setting,
            tone=comic.tone,
            art_style=comic.art_style,
        )

        # Update panel fields
        panel.title = str(panel_data.get("title", panel.title))
        panel.scene_description = str(panel_data.get("scene_description", panel.scene_description))
        panel.narration = str(panel_data.get("narration", panel.narration))
        panel.dialogue = json.dumps(panel_data.get("dialogue", []))
        panel.image_prompt = str(panel_data.get("image_prompt", panel.image_prompt))
        panel.generation_status = "PENDING"
        db.commit()

        _update_job(db, job, "RUNNING", f"Generating image for panel {panel.panel_number}...")

        # Regenerate image
        image_svc.generate_panel_image(
            db=db,
            panel=panel,
            character_profile=char_profile,
            art_style=comic.art_style,
        )

        # If panel 1 regenerated, update thumbnail
        if panel.panel_number == 1 and panel.image_path:
            comic.thumbnail_path = panel.image_path
            db.commit()

        _update_job(db, job, "COMPLETED", f"Panel {panel.panel_number} ready!")

    except Exception as e:
        logger.exception(f"Panel regeneration failed: {e}")
        _update_job(db, job, "FAILED", error=str(e))


def run_story_continuation(
    db: Session,
    parent_comic: Comic,
    new_comic: Comic,
    job: GenerationJob,
) -> None:
    """Generate a continuation chapter from a parent comic."""
    try:
        _update_job(db, job, "RUNNING", "Planning the next chapter...")

        parent_char_profile = char_svc.get_profile_dict(parent_comic.character) if parent_comic.character else {}

        # Build summary of previous panels
        prev_panels = sorted(parent_comic.panels, key=lambda p: p.panel_number)
        prev_summary_parts = [f"Panel {p.panel_number}: {p.scene_description}" for p in prev_panels]
        prev_panels_summary = " | ".join(prev_summary_parts)

        outline = story_svc.generate_continuation(
            previous_title=parent_comic.title,
            previous_summary=parent_comic.summary or "",
            character_profile=parent_char_profile,
            setting=parent_comic.setting,
            tone=parent_comic.tone,
            art_style=parent_comic.art_style,
            chapter_number=new_comic.chapter_number,
            previous_panels_summary=prev_panels_summary,
        )

        new_comic.title = outline.get("title", new_comic.title)
        new_comic.summary = outline.get("summary", "")
        db.commit()

        _update_job(db, job, "RUNNING", "Creating character profile...")

        char_profile_data = outline.get("character_profile", parent_char_profile)
        character = char_svc.create_from_profile(db, new_comic.id, char_profile_data)
        char_profile = char_svc.get_profile_dict(character)

        _update_job(db, job, "RUNNING", "Writing panel narrations...")

        panels_data = outline.get("panels", [])
        db_panels: list[Panel] = []
        for p_data in panels_data:
            dialogue = p_data.get("dialogue", [])
            panel = Panel(
                comic_id=new_comic.id,
                panel_number=int(p_data.get("panel_number", 1)),
                title=str(p_data.get("title", "")),
                scene_description=str(p_data.get("scene_description", "")),
                narration=str(p_data.get("narration", "")),
                dialogue=json.dumps(dialogue),
                image_prompt=str(p_data.get("image_prompt", "")),
                generation_status="PENDING",
            )
            db.add(panel)
            db_panels.append(panel)
        db.commit()

        _update_job(db, job, "RUNNING", "Generating illustrations...")

        image_svc.generate_all_panel_images(
            db=db,
            panels=db_panels,
            character_profile=char_profile,
            art_style=new_comic.art_style,
        )

        if db_panels and db_panels[0].image_path:
            new_comic.thumbnail_path = db_panels[0].image_path
            db.commit()

        _update_job(db, job, "COMPLETED", "Chapter ready!")
        logger.info(f"Continuation comic {new_comic.id} (chapter {new_comic.chapter_number}) complete.")

    except Exception as e:
        logger.exception(f"Story continuation failed: {e}")
        _update_job(db, job, "FAILED", error=str(e))
