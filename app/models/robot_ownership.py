"""Robot Ownership model"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from app.database import Base
from app.models.robot import utcnow

class RobotOwnership(Base):
    """Mapping between a robot and a user"""
    __tablename__ = "robot_ownerships"

    id = Column(Integer, primary_key=True, index=True)
    robot_id = Column(Integer, ForeignKey("robots.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    role = Column(String(50), default="OWNER", nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
