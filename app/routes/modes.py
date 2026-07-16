from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.auth import get_current_user_id
from app.services.command_service import create_command
from app.services.kafka_service import publish_kafka_event
from app.services.mqtt_service import publish_mqtt_message
from app.utils.dates import utc_now_naive
from app.utils.ownership import verify_robot_ownership

router = APIRouter(prefix="/robots", tags=["Modes"])

class ModeChangeRequest(BaseModel):
    mode: Literal[
        "IDLE", 
        "MANUAL", 
        "LINE_FOLLOWING", 
        "OBSTACLE_AVOIDANCE", 
        "PATROL", 
        "FOLLOW_PERSON", 
        "RETURN_TO_DOCK", 
        "CHARGING"
    ]

@router.post("/{robot_id}/mode", status_code=status.HTTP_202_ACCEPTED)
async def change_mode(
    robot_id: str,
    request: ModeChangeRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Change the operating mode of the robot."""
    robot = verify_robot_ownership(db, robot_id, user_id)
    
    # 1. Verify robot is online
    if robot.connection_status != "ONLINE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change mode: Robot is offline"
        )
        
    # 2. Reject if emergency stop is active
    if robot.emergency_stop_active or robot.current_mode == "EMERGENCY_STOP":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change mode: Emergency Stop is active"
        )
        
    # 3. Create persistent DB command
    expires_at = utc_now_naive() + timedelta(seconds=10)
    cmd = create_command(
        db=db,
        robot_id=robot_id,
        issued_by_user_id=user_id,
        command_type="MODE_CHANGE",
        payload={"mode": request.mode},
        priority=1,
        expires_at=expires_at
    )
    
    # 4. Publish MQTT command
    import asyncio
    payload = {
        "command_id": cmd.id,
        "mode": request.mode,
        "issued_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }
    asyncio.create_task(publish_mqtt_message(
        topic=f"rex/robots/{robot_id}/commands/mode",
        payload=payload
    ))
    
    # Publish Kafka event
    asyncio.create_task(publish_kafka_event(
        topic="rex.robot.mode-changed.v1",
        event_type="robot_mode_change_requested",
        payload={
            "robot_id": robot_id,
            "command_id": cmd.id,
            "mode": request.mode
        }
    ))
    
    return {
        "message": "Mode change command issued",
        "command_id": cmd.id,
        "mode": request.mode
    }
