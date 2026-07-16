from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base

if TYPE_CHECKING:
    from app.models.robot import Robot


def utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class RobotDeviceSession(Base):
    __tablename__ = "robot_device_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    robot_id: Mapped[str] = mapped_column(String(36), ForeignKey("robots.id", ondelete="CASCADE"), nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=utc_now_naive, 
        onupdate=utc_now_naive, 
        nullable=False
    )
    access_expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    refresh_expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    robot: Mapped["Robot"] = relationship("Robot", back_populates="sessions")
