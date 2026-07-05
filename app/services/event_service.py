"""Event Service for logging robot events"""

from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.models.robot_event import RobotEvent

class EventService:
    """Service to log events related to robots"""

    @staticmethod
    def log_event(
        db: Session,
        robot_id: int,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None
    ) -> RobotEvent:
        """Log an event for a specific robot."""
        event = RobotEvent(
            robot_id=robot_id,
            event_type=event_type,
            payload=payload
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

event_service = EventService()
