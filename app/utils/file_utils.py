"""File management utilities."""
import os
import uuid
from pathlib import Path

STORAGE_ROOT = Path("storage")
COMICS_DIR = STORAGE_ROOT / "comics"
EXPORTS_DIR = STORAGE_ROOT / "exports"
TEMP_DIR = STORAGE_ROOT / "temp"


def ensure_comic_dirs(comic_id: str) -> Path:
    """Create and return the panels directory for a given comic."""
    panels_dir = COMICS_DIR / comic_id / "panels"
    panels_dir.mkdir(parents=True, exist_ok=True)
    return panels_dir


def panel_image_path(comic_id: str, panel_number: int, ext: str = "png") -> Path:
    """Return the absolute path for a panel image."""
    panels_dir = ensure_comic_dirs(comic_id)
    return panels_dir / f"panel_{panel_number}.{ext}"


def export_pdf_path(comic_id: str) -> Path:
    """Return the absolute path for a comic PDF export."""
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return EXPORTS_DIR / f"{comic_id}.pdf"


def image_url_from_path(path: str | Path | None) -> str | None:
    """Convert a storage path or URL to a web-accessible URL."""
    if not path:
        return None
    path_str = str(path).strip()
    if not path_str:
        return None

    # If it's already an absolute or relative web URL
    if path_str.startswith(("http://", "https://", "data:image/", "/storage/", "/static/")):
        return path_str

    try:
        p = Path(path_str).resolve()
        storage_root = STORAGE_ROOT.resolve()
        try:
            rel = p.relative_to(storage_root)
            return f"/storage/{rel.as_posix()}"
        except ValueError:
            pass
    except Exception:
        pass

    # Fallback string parsing
    normalized = path_str.replace("\\", "/")
    if "storage/" in normalized:
        idx = normalized.find("storage/")
        return "/" + normalized[idx:]
    if normalized.startswith("static/"):
        return "/" + normalized

    return None


def new_id() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


def safe_filename(name: str, ext: str = "png") -> str:
    """Generate a safe unique filename."""
    return f"{new_id()}.{ext}"
