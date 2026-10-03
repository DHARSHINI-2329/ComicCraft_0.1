"""Comic API routes: generate, regenerate, continue, favorite, delete, PDF."""
import logging
import threading
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.models.comic import Comic
from app.routes.auth import require_user, get_current_user
from app.schemas.comic import ComicCreateRequest, GenerateComicResponse, ComicResponse
from app.schemas.generation import JobStatusResponse
from app.services.comic_service import ComicService
from app.services.generation_service import run_full_generation, run_panel_regeneration, run_story_continuation
from app.utils.file_utils import export_pdf_path
from app.services.pdf_service import PDFService
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["comics"])

comic_svc = ComicService()
pdf_svc = PDFService()


def _run_in_thread(target, *args):
    """Run a blocking generation function in a background thread."""
    t = threading.Thread(target=target, args=args, daemon=True)
    t.start()


# ── Comic Generation ───────────────────────────────────────────────────────────

@router.post("/generate-comic/json", response_model=GenerateComicResponse)
async def generate_comic_json(
    data: ComicCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Create a new comic and start generation pipeline. Returns job info."""
    comic = comic_svc.create_comic_record(
        db=db,
        user_id=current_user.id,
        story_prompt=data.story_prompt,
        character_name=data.character_name,
        character_description=data.character_description,
        setting=data.setting,
        tone=data.tone,
        art_style=data.art_style,
    )
    job = comic_svc.create_job(db=db, comic_id=comic.id, job_type="FULL_COMIC")
    _run_in_thread(run_full_generation, comic.id, job.id)

    return GenerateComicResponse(
        success=True,
        comic_id=comic.id,
        title=comic.title,
        status="PENDING",
        job_id=job.id,
        message="Generation started. Poll /api/jobs/{job_id} for status.",
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Poll generation job status."""
    job = comic_svc.get_job(db=db, job_id=job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse.model_validate(job)


# ── Comic Retrieval ────────────────────────────────────────────────────────────

@router.get("/comics/{comic_id}", response_model=ComicResponse)
async def get_comic(
    comic_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Get full comic data including panels."""
    comic = comic_svc.get_comic(db=db, comic_id=comic_id, user_id=current_user.id)
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")
    return comic_svc.comic_to_response(comic)


# ── Panel Regeneration ─────────────────────────────────────────────────────────

@router.post("/comics/{comic_id}/panel/{panel_number}/regenerate")
async def regenerate_panel(
    comic_id: str,
    panel_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Regenerate a single panel image and story content."""
    comic = comic_svc.get_comic(db=db, comic_id=comic_id, user_id=current_user.id)
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")
    panel = comic_svc.get_panel(db=db, comic_id=comic_id, panel_number=panel_number)
    if not panel:
        raise HTTPException(status_code=404, detail="Panel not found")
    job = comic_svc.create_job(db=db, comic_id=comic.id, job_type="PANEL", panel_number=panel_number)
    _run_in_thread(run_panel_regeneration, comic.id, panel.panel_number, job.id)
    return {"success": True, "job_id": job.id, "panel_number": panel_number}


# ── Full Comic Regeneration ────────────────────────────────────────────────────

@router.post("/comics/{comic_id}/regenerate")
async def regenerate_comic(
    comic_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Regenerate the entire comic (new story + new images)."""
    comic = comic_svc.get_comic(db=db, comic_id=comic_id, user_id=current_user.id)
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")
    # Delete existing panels
    for panel in comic.panels:
        db.delete(panel)
    if comic.character:
        db.delete(comic.character)
    db.commit()
    job = comic_svc.create_job(db=db, comic_id=comic.id, job_type="FULL_COMIC")
    _run_in_thread(run_full_generation, comic.id, job.id)
    return {"success": True, "job_id": job.id, "comic_id": comic.id}


# ── Story Continuation ─────────────────────────────────────────────────────────

@router.post("/comics/{comic_id}/continue")
async def continue_story(
    comic_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Create a new chapter comic continuing from the given comic."""
    parent_comic = comic_svc.get_comic(db=db, comic_id=comic_id, user_id=current_user.id)
    if not parent_comic:
        raise HTTPException(status_code=404, detail="Comic not found")

    new_chapter = parent_comic.chapter_number + 1
    new_comic = comic_svc.create_comic_record(
        db=db,
        user_id=current_user.id,
        story_prompt=parent_comic.story_prompt,
        character_name=parent_comic.character_name,
        character_description=parent_comic.character_description,
        setting=parent_comic.setting,
        tone=parent_comic.tone,
        art_style=parent_comic.art_style,
        chapter_number=new_chapter,
        parent_comic_id=parent_comic.id,
    )
    job = comic_svc.create_job(db=db, comic_id=new_comic.id, job_type="FULL_COMIC")
    _run_in_thread(run_story_continuation, parent_comic.id, new_comic.id, job.id)

    return {
        "success": True,
        "comic_id": new_comic.id,
        "job_id": job.id,
        "chapter_number": new_chapter,
    }


# ── Favorites ─────────────────────────────────────────────────────────────────

@router.post("/comics/{comic_id}/favorite")
async def toggle_favorite(
    comic_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Toggle the favorite status of a comic."""
    comic = comic_svc.get_comic(db=db, comic_id=comic_id, user_id=current_user.id)
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")
    comic = comic_svc.toggle_favorite(db=db, comic=comic)
    return {"success": True, "is_favorite": comic.is_favorite}


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/comics/{comic_id}")
async def delete_comic(
    comic_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Delete a comic and all its data."""
    comic = comic_svc.get_comic(db=db, comic_id=comic_id, user_id=current_user.id)
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")
    comic_svc.delete_comic(db=db, comic=comic)
    return {"success": True, "message": "Comic deleted"}


# ── PDF Export ────────────────────────────────────────────────────────────────

@router.get("/comics/{comic_id}/pdf")
async def download_pdf(
    comic_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Generate (or serve cached) PDF for a comic."""
    comic = comic_svc.get_comic(db=db, comic_id=comic_id, user_id=current_user.id)
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")
    if not comic.panels:
        raise HTTPException(status_code=400, detail="Comic has no panels yet")
    try:
        pdf_path = pdf_svc.export_comic_to_pdf(db=db, comic=comic)
        safe_title = "".join(c for c in comic.title if c.isalnum() or c in " -_")[:50]
        filename = f"ComicCraft_{safe_title}_Ch{comic.chapter_number}.pdf"
        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename=filename,
        )
    except Exception as e:
        logger.exception(f"PDF generation failed for {comic_id}: {e}")
        raise HTTPException(status_code=500, detail="PDF generation failed")


# ── Test Image ────────────────────────────────────────────────────────────────

@router.post("/test-image")
async def test_image_generation(current_user: User = Depends(require_user)):
    """Development endpoint: test image provider availability."""
    from app.ai.image_provider import get_image_provider
    provider = get_image_provider()
    return {
        "provider": type(provider).__name__,
        "available": provider.is_available(),
    }
