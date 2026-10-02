"""ComicCraft FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info(f"Starting {settings.app_name}...")
    # Ensure storage directories exist
    for d in ["storage/comics", "storage/exports", "storage/temp"]:
        Path(d).mkdir(parents=True, exist_ok=True)
    # Initialize database
    init_db()
    logger.info("Database initialized.")
    if settings.demo_mode:
        logger.warning("=" * 50)
        logger.warning("  DEMO MODE IS ACTIVE — No real AI calls will be made.")
        logger.warning("=" * 50)
    yield
    logger.info("Shutting down ComicCraft.")


app = FastAPI(
    title="ComicCraft — AI Comic Story Creator",
    description="Transform story ideas into illustrated comics with AI.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

# Routers
from app.routes import web, auth, comics  # noqa: E402

app.include_router(web.router)
app.include_router(auth.router)
app.include_router(comics.router)


# Health check
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "demo_mode": settings.demo_mode,
        "image_provider": settings.image_provider,
        "gemini_configured": bool(settings.gemini_api_key),
    }


# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
    )
