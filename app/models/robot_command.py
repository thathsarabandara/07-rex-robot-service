from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base

if TYPE_CHECKING:
    from app.models.robot import Robot


def utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class RobotCommand(Base):
    __tablename__ = "robot_commands"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    robot_id: Mapped[str] = mapped_column(String(36), ForeignKey("robots.id", ondelete="CASCADE"), nullable=False)
    issued_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    command_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    
    # PENDING, PUBLISHED, ACKNOWLEDGED, EXECUTING, COMPLETED, REJECTED, FAILED, EXPIRED
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, nullable=False)

    # Relationships
    robot: Mapped["Robot"] = relationship("Robot", back_populates="commands")
