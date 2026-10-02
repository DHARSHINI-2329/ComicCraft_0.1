"""Web routes: serve HTML templates."""
import logging
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.routes.auth import get_current_user
from app.services.comic_service import ComicService
from app.models.user import User
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")
comic_svc = ComicService()
settings = get_settings()


def _ctx(request: Request, user: User | None, **kwargs) -> dict:
    """Build a base template context."""
    return {
        "user": user,
        "demo_mode": settings.demo_mode,
        **kwargs,
    }


@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    return templates.TemplateResponse(request, "index.html", _ctx(request, user))


@router.get("/create", response_class=HTMLResponse)
async def create_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/create", status_code=302)
    return templates.TemplateResponse(request, "create.html", _ctx(request, user))


@router.get("/generating/{comic_id}", response_class=HTMLResponse)
async def generating_page(comic_id: str, job_id: str = "", request: Request = None, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request, "generating.html", _ctx(request, user, comic_id=comic_id, job_id=job_id))


@router.get("/comic/{comic_id}", response_class=HTMLResponse)
async def comic_preview(comic_id: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    comic = comic_svc.get_comic(db=db, comic_id=comic_id, user_id=user.id)
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")
    comic_data = comic_svc.comic_to_response(comic)
    return templates.TemplateResponse(request, "comic_preview.html", _ctx(
        request, user,
        comic=comic_data,
    ))


@router.get("/library", response_class=HTMLResponse)
async def library(
    request: Request,
    db: Session = Depends(get_db),
    search: str = "",
    filter: str = "all",
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    favorites_only = filter == "favorites"
    comics = comic_svc.list_user_comics(
        db=db,
        user_id=user.id,
        favorites_only=favorites_only,
        search=search or None,
    )
    comics_data = [comic_svc.comic_to_response(c) for c in comics]
    return templates.TemplateResponse(request, "library.html", _ctx(
        request, user,
        comics=comics_data,
        search=search,
        filter=filter,
    ))


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    all_comics = comic_svc.list_user_comics(db=db, user_id=user.id)
    favorites = [c for c in all_comics if c.is_favorite]
    chapters = [c for c in all_comics if c.chapter_number > 1]
    recent = all_comics[:6]
    recent_data = [comic_svc.comic_to_response(c) for c in recent]
    return templates.TemplateResponse(request, "dashboard.html", _ctx(
        request, user,
        total_comics=len(all_comics),
        total_favorites=len(favorites),
        total_chapters=len(chapters),
        recent_comics=recent_data,
    ))


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db), next: str = "/dashboard"):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request, "login.html", _ctx(request, user, next=next))


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request, "register.html", _ctx(request, user))


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    all_comics = comic_svc.list_user_comics(db=db, user_id=user.id)
    return templates.TemplateResponse(request, "profile.html", _ctx(
        request, user,
        total_comics=len(all_comics),
    ))


@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    return templates.TemplateResponse(request, "about.html", _ctx(request, user))


@router.get("/export-success/{comic_id}", response_class=HTMLResponse)
async def export_success(comic_id: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    comic = comic_svc.get_comic(db=db, comic_id=comic_id, user_id=user.id)
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")
    return templates.TemplateResponse(request, "export_success.html", _ctx(
        request, user,
        comic=comic_svc.comic_to_response(comic),
    ))
