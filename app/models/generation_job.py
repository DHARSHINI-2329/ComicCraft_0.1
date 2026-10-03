"""GenerationJob model for tracking async comic generation tasks."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.database import Base

if TYPE_CHECKING:
    from app.models.comic import Comic


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    comic_id: Mapped[str] = mapped_column(String(36), ForeignKey("comics.id"), nullable=False)
    job_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # FULL_COMIC | PANEL | STORY | IMAGE | PDF
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    # PENDING | RUNNING | COMPLETED | FAILED
    current_step: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    panel_number: Mapped[Optional[int]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    comic: Mapped[Comic] = relationship("Comic", back_populates="generation_jobs")
