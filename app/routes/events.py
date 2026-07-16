from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.auth import get_current_user_id
from app.models.robot_event import RobotEvent
from app.schemas.event import RobotEventResponse
from app.utils.ownership import verify_robot_ownership

router = APIRouter(prefix="/robots", tags=["Events"])

@router.get("/{robot_id}/events", response_model=list[RobotEventResponse])
async def get_events(
    robot_id: str,
    limit: int = 50,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Retrieve event history for a claimed robot."""
    verify_robot_ownership(db, robot_id, user_id)
    events = db.query(RobotEvent).filter(
        RobotEvent.robot_id == robot_id
    ).order_by(RobotEvent.occurred_at.desc()).limit(limit).offset(offset).all()
    return events
