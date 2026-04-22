"""Data models for the application"""

from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Boolean,
    JSON,
)
from sqlalchemy.orm import relationship

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


class DeviceType(str, Enum):
    """Type of IoT device"""
    ROBOT_PRIMARY = "ROBOT_PRIMARY"
    ROBOT_SECONDARY = "ROBOT_SECONDARY"
    SENSOR = "SENSOR"
    ACTUATOR = "ACTUATOR"
    EDGE_COMPUTE = "EDGE_COMPUTE"


class AuthenticationStatus(str, Enum):
    """Authentication session status"""
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class Robot(Base):
    """Robot entity representing a physical or virtual robot"""
    __tablename__ = "robots"

    id = Column(Integer, primary_key=True, index=True)
    robot_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    model = Column(String(255), nullable=False)
    serial_number = Column(String(255), unique=True, nullable=False, index=True)
    firmware_version = Column(String(50), nullable=False)
    status = Column(
        SQLEnum(RobotStatus),
        default=RobotStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    devices = relationship("Device", back_populates="robot", cascade="all, delete-orphan")
    auth_sessions = relationship("AuthenticationSession", back_populates="robot", cascade="all, delete-orphan")
    fingerprints = relationship("DeviceFingerprint", back_populates="robot", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("robot_id", name="uq_robot_id"),
        UniqueConstraint("serial_number", name="uq_serial_number"),
    )


class Device(Base):
    """Device associated with a robot"""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), unique=True, nullable=False, index=True)
    robot_id = Column(Integer, ForeignKey("robots.id"), nullable=False, index=True)
    device_type = Column(
        SQLEnum(DeviceType),
        default=DeviceType.ROBOT_PRIMARY,
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    mac_address = Column(String(17), unique=True, nullable=False)
    ip_address = Column(String(45), nullable=True)
    public_key = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    robot = relationship("Robot", back_populates="devices")
    fingerprints = relationship("DeviceFingerprint", back_populates="device", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("device_id", name="uq_device_id"),
    )


class DeviceFingerprint(Base):
    """Device fingerprint for identity verification"""
    __tablename__ = "device_fingerprints"

    id = Column(Integer, primary_key=True, index=True)
    fingerprint_hash = Column(String(256), unique=True, nullable=False, index=True)
    robot_id = Column(Integer, ForeignKey("robots.id"), nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True, index=True)
    
    # Fingerprint components
    hardware_id = Column(String(255), nullable=False)
    mac_address = Column(String(17), nullable=False)
    cpu_info = Column(String(255), nullable=False)
    os_info = Column(String(255), nullable=False)
    system_uuid = Column(String(255), nullable=False)

    # Metadata
    fingerprint_method = Column(String(50), default="combined", nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    robot = relationship("Robot", back_populates="fingerprints")
    device = relationship("Device", back_populates="fingerprints")

    __table_args__ = (
        UniqueConstraint("fingerprint_hash", name="uq_fingerprint_hash"),
    )


class AuthenticationSession(Base):
    """Authentication session for robot JWT tokens"""
    __tablename__ = "authentication_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    robot_id = Column(Integer, ForeignKey("robots.id"), nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    
    # Token information
    access_token_jti = Column(String(64), nullable=False, index=True)
    refresh_token_jti = Column(String(64), nullable=False, index=True)
    
    # Session details
    status = Column(
        SQLEnum(AuthenticationStatus),
        default=AuthenticationStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    fingerprint_hash = Column(String(256), nullable=True)

    # Token expiry
    access_token_expires_at = Column(DateTime(timezone=True), nullable=False)
    refresh_token_expires_at = Column(DateTime(timezone=True), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    robot = relationship("Robot", back_populates="auth_sessions")

    __table_args__ = (
        UniqueConstraint("access_token_jti", name="uq_access_token_jti"),
        UniqueConstraint("refresh_token_jti", name="uq_refresh_token_jti"),
    )


class LoginAttempt(Base):
    """Track robot login attempts for security"""
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, index=True)
    robot_id = Column(Integer, ForeignKey("robots.id"), nullable=False, index=True)
    ip_address = Column(String(45), nullable=False)
    fingerprint_hash = Column(String(256), nullable=True)
    success = Column(Boolean, nullable=False)
    error_message = Column(String(255), nullable=True)
    attempted_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
