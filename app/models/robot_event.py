"""Robot Event model"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from app.database import Base
from app.models.robot import utcnow

class RobotEvent(Base):
    """Event log for robot operations"""
    __tablename__ = "robot_events"

    id = Column(Integer, primary_key=True, index=True)
    robot_id = Column(Integer, ForeignKey("robots.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
