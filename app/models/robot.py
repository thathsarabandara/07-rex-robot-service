from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base

if TYPE_CHECKING:
    from app.models.device_session import RobotDeviceSession
    from app.models.robot_command import RobotCommand
    from app.models.robot_configuration import RobotConfiguration
    from app.models.robot_event import RobotEvent


def utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Robot(Base):
    __tablename__ = "robots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    serial_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hardware_model: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    device_secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    firmware_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # UNCLAIMED, CLAIMED, DISABLED
    status: Mapped[str] = mapped_column(String(50), default="UNCLAIMED", nullable=False)
    # OFFLINE, CONNECTING, ONLINE, DEGRADED
    connection_status: Mapped[str] = mapped_column(String(50), default="OFFLINE", nullable=False)
    # IDLE, MANUAL, LINE_FOLLOWING, OBSTACLE_AVOIDANCE, PATROL, FOLLOW_PERSON, RETURN_TO_DOCK, CHARGING, EMERGENCY_STOP
    current_mode: Mapped[str] = mapped_column(String(50), default="IDLE", nullable=False)
    
    emergency_stop_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    secret_rotation_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=utc_now_naive, 
        onupdate=utc_now_naive, 
        nullable=False
    )

    # Relationships
    configuration: Mapped["RobotConfiguration"] = relationship(
        "RobotConfiguration", 
        back_populates="robot", 
        uselist=False, 
        cascade="all, delete-orphan"
    )
    sessions: Mapped[list["RobotDeviceSession"]] = relationship(
        "RobotDeviceSession", 
        back_populates="robot", 
        cascade="all, delete-orphan"
    )
    commands: Mapped[list["RobotCommand"]] = relationship(
        "RobotCommand", 
        back_populates="robot", 
        cascade="all, delete-orphan"
    )
    events: Mapped[list["RobotEvent"]] = relationship(
        "RobotEvent", 
        back_populates="robot", 
        cascade="all, delete-orphan"
    )
