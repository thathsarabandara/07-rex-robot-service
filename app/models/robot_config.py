"""Robot Configuration model definition"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database import Base


class RobotConfig(Base):
    """Runtime configuration settings for physical robots"""
    __tablename__ = "robot_configs"

    id = Column(String(36), primary_key=True)
    robot_id = Column(String(36), ForeignKey("robots.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    max_speed = Column(Integer, default=180, nullable=False)
    turn_speed = Column(Integer, default=140, nullable=False)
    acceleration_step = Column(Integer, default=10, nullable=False)
    obstacle_stop_distance_cm = Column(Integer, default=20, nullable=False)
    telemetry_interval_ms = Column(Integer, default=1000, nullable=False)
    led_brightness = Column(Integer, default=80, nullable=False)
    
    camera_pan_min = Column(Integer, default=0, nullable=False)
    camera_pan_max = Column(Integer, default=180, nullable=False)
    camera_tilt_min = Column(Integer, default=30, nullable=False)
    camera_tilt_max = Column(Integer, default=150, nullable=False)

    config_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    robot = relationship("Robot", back_populates="config")
