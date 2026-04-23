"""Data models for the application"""

from datetime import datetime, timedelta, timezone
from enum import Enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLEnum,
    Integer,
    String,
    UniqueConstraint,
)

from app.database import Base


def utcnow() -> datetime:
    """Return current UTC time"""
    return datetime.now(timezone.utc)


class RobotStatus(str, Enum):
    """Robot operational status"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    DEACTIVATED = "DEACTIVATED"





class Robot(Base):
    """Robot entity representing a physical or virtual robot"""
    __tablename__ = "robots"

    id = Column(Integer, primary_key=True, index=True)
    robot_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    model = Column(String(255), nullable=False)
    serial_number = Column(String(255), unique=True, nullable=False, index=True)
    owner_id = Column(String(64), nullable=True, index=True)
    status = Column(
        SQLEnum(RobotStatus),
        default=RobotStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("robot_id", name="uq_robot_id"),
        UniqueConstraint("serial_number", name="uq_serial_number"),
    )
