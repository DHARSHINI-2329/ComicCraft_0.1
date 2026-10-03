"""Character model."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.database import Base

if TYPE_CHECKING:
    from app.models.comic import Comic


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    comic_id: Mapped[str] = mapped_column(String(36), ForeignKey("comics.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    appearance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    personality: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    clothing: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    visual_identifiers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    species: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    age: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    comic: Mapped[Comic] = relationship("Comic", back_populates="character")
