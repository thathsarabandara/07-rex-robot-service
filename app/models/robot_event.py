"""Robot Event model definition"""

from enum import Enum as PyEnum
from sqlalchemy import Column, String, Enum, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database import Base


class EventSeverity(str, PyEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RobotEvent(Base):
    """Event logs emitted or received for a robot"""
    __tablename__ = "robot_events"

    id = Column(String(36), primary_key=True)
    robot_id = Column(String(36), ForeignKey("robots.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    
    severity = Column(Enum(EventSeverity), default=EventSeverity.LOW, nullable=False)
    source = Column(String(100), nullable=True)
    payload = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    robot = relationship("Robot", back_populates="events")
