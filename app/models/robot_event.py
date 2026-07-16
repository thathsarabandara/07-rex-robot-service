from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base

if TYPE_CHECKING:
    from app.models.robot import Robot


def utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class RobotEvent(Base):
    __tablename__ = "robot_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    robot_id: Mapped[str] = mapped_column(String(36), ForeignKey("robots.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # INFO, WARNING, CRITICAL
    severity: Mapped[str] = mapped_column(String(50), default="INFO", nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON, name="metadata", nullable=True)
    
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, nullable=False)

    # Relationships
    robot: Mapped["Robot"] = relationship("Robot", back_populates="events")
