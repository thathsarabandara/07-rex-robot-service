"""Robot model definition"""

from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Enum, DateTime, func
from sqlalchemy.orm import relationship

from app.database import Base


class RobotStatus(str, PyEnum):
    UNPAIRED = "UNPAIRED"
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DISABLED = "DISABLED"


class RobotMode(str, PyEnum):
    IDLE = "IDLE"
    MANUAL = "MANUAL"
    PATROL = "PATROL"
    FOLLOW = "FOLLOW"
    AUTONOMOUS = "AUTONOMOUS"
    CHARGING = "CHARGING"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class Robot(Base):
    """Represents a physical robot in the REX system"""
    __tablename__ = "robots"

    id = Column(String(36), primary_key=True)
    robot_code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    owner_user_id = Column(String(36), nullable=True, index=True)
    firmware_version = Column(String(50), nullable=True)
    hardware_version = Column(String(50), nullable=True)
    
    status = Column(
        Enum(RobotStatus), 
        default=RobotStatus.UNPAIRED, 
        nullable=False
    )
    mode = Column(
        Enum(RobotMode), 
        default=RobotMode.IDLE, 
        nullable=False
    )
    
    last_seen_at = Column(DateTime, nullable=True)
    paired_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    pairing_codes = relationship("RobotPairingCode", back_populates="robot", cascade="all, delete-orphan")
    config = relationship("RobotConfig", back_populates="robot", uselist=False, cascade="all, delete-orphan")
    commands = relationship("RobotCommand", back_populates="robot", cascade="all, delete-orphan")
    state = relationship("RobotState", back_populates="robot", uselist=False, cascade="all, delete-orphan")
    events = relationship("RobotEvent", back_populates="robot", cascade="all, delete-orphan")
