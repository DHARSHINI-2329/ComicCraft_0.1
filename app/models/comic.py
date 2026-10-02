"""Comic model."""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.database import Base


class Comic(Base):
    __tablename__ = "comics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    story_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    character_name: Mapped[str] = mapped_column(String(100), nullable=False)
    character_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    setting: Mapped[str] = mapped_column(String(100), nullable=False)
    tone: Mapped[str] = mapped_column(String(50), nullable=False)
    art_style: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chapter_number: Mapped[int] = mapped_column(Integer, default=1)
    parent_comic_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("comics.id"), nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="comics")
    panels: Mapped[list["Panel"]] = relationship("Panel", back_populates="comic", cascade="all, delete-orphan", order_by="Panel.panel_number")
    character: Mapped[Optional["Character"]] = relationship("Character", back_populates="comic", uselist=False, cascade="all, delete-orphan")
    generation_jobs: Mapped[list["GenerationJob"]] = relationship("GenerationJob", back_populates="comic", cascade="all, delete-orphan")
    continuations: Mapped[list["Comic"]] = relationship("Comic", foreign_keys=[parent_comic_id])
