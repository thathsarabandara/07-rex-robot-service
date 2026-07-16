from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base

if TYPE_CHECKING:
    from app.models.robot import Robot


def utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class RobotConfiguration(Base):
    __tablename__ = "robot_configurations"

    robot_id: Mapped[str] = mapped_column(String(36), ForeignKey("robots.id", ondelete="CASCADE"), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Base speeds
    base_max_speed: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    base_default_speed: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    turn_speed: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    acceleration_step: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    braking_step: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    
    # Joystick properties
    joystick_dead_zone: Mapped[float] = mapped_column(Float, default=0.05, nullable=False)
    joystick_timeout_ms: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    
    # Obstacle distance
    obstacle_stop_distance_cm: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    
    # Arm joint angle limits
    arm_base_min_angle: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    arm_base_max_angle: Mapped[int] = mapped_column(Integer, default=180, nullable=False)
    arm_shoulder_min_angle: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    arm_shoulder_max_angle: Mapped[int] = mapped_column(Integer, default=180, nullable=False)
    arm_elbow_min_angle: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    arm_elbow_max_angle: Mapped[int] = mapped_column(Integer, default=180, nullable=False)
    arm_grip_min_angle: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    arm_grip_max_angle: Mapped[int] = mapped_column(Integer, default=180, nullable=False)
    arm_default_speed: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    
    # Intervals & peripherals
    heartbeat_interval_seconds: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    heartbeat_timeout_seconds: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    telemetry_interval_ms: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    
    buzzer_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    oled_eyes_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    automatic_night_light: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=utc_now_naive, 
        onupdate=utc_now_naive, 
        nullable=False
    )

    # Relationships
    robot: Mapped["Robot"] = relationship("Robot", back_populates="configuration")
