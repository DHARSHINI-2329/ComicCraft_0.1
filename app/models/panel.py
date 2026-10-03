"""Panel model."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.database import Base

if TYPE_CHECKING:
    from app.models.comic import Comic


class Panel(Base):
    __tablename__ = "panels"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    comic_id: Mapped[str] = mapped_column(String(36), ForeignKey("comics.id"), nullable=False)
    panel_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    scene_description: Mapped[str] = mapped_column(Text, nullable=False)
    narration: Mapped[str] = mapped_column(Text, nullable=False)
    dialogue: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    image_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    image_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    generation_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    comic: Mapped[Comic] = relationship("Comic", back_populates="panels")
