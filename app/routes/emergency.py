import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.redis import redis_client
from app.middleware.auth import get_current_user_id
from app.models.robot_command import RobotCommand
from app.models.robot_event import RobotEvent
from app.schemas.command import CommandResponse
from app.services.command_service import get_command_by_id
from app.services.control_lease_service import get_lease_key
from app.services.kafka_service import publish_kafka_event
from app.services.mqtt_service import publish_mqtt_message
from app.services.websocket_service import broadcast_to_robot
from app.utils.dates import utc_now_naive
from app.utils.ownership import verify_robot_ownership

router = APIRouter(prefix="/robots", tags=["Emergency Stop"])

@router.post("/{robot_id}/emergency-stop", status_code=status.HTTP_200_OK)
async def trigger_emergency_stop(
    robot_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Trigger an emergency stop, forcing robot to halt immediately."""
    robot = verify_robot_ownership(db, robot_id, user_id)
    
    # 1. Update DB model
    robot.emergency_stop_active = True
    robot.current_mode = "EMERGENCY_STOP"
    robot.updated_at = utc_now_naive()
    
    # 2. Revoke active control lease
    import asyncio
    asyncio.create_task(redis_client.delete(get_lease_key(robot_id)))
    
    # 3. Fail pending commands
    db.query(RobotCommand).filter(
        RobotCommand.robot_id == robot_id,
        RobotCommand.status.in_(["PENDING", "PUBLISHED"])
    ).update({
        "status": "FAILED",
        "failure_reason": "EMERGENCY_STOP_TRIGGERED",
        "completed_at": utc_now_naive()
    }, synchronize_session=False)
    
    # 4. Record critical event
    db_event = RobotEvent(
        robot_id=robot_id,
        event_type="emergency_stop",
        severity="CRITICAL",
        message="Emergency stop activated by user request"
    )
    db.add(db_event)
    
    # Create command
    cmd_id = str(uuid.uuid4())
    cmd = RobotCommand(
        id=cmd_id,
        robot_id=robot_id,
        issued_by_user_id=user_id,
        command_type="EMERGENCY_STOP",
        payload={"active": True, "reason": "USER_REQUEST"},
        status="PUBLISHED",
        priority=10,
        expires_at=utc_now_naive() + timedelta(seconds=10)
    )
    db.add(cmd)
    db.commit()
    
    # 5. Publish MQTT QoS 1
    payload = {
        "command_id": cmd_id,
        "active": True,
        "reason": "USER_REQUEST",
        "issued_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }
    asyncio.create_task(publish_mqtt_message(
        topic=f"rex/robots/{robot_id}/commands/emergency-stop",
        payload=payload,
        qos=1
    ))
    
    # 6. Notify WebSocket clients
    asyncio.create_task(broadcast_to_robot(
        robot_id=robot_id,
        message={
            "type": "STATUS_UPDATE",
            "robot_id": robot_id,
            "connection_status": robot.connection_status,
            "mode": "EMERGENCY_STOP",
            "emergency_stop_active": True,
            "last_seen_at": robot.last_seen_at.isoformat() if robot.last_seen_at else None
        }
    ))
    
    # 7. Publish Kafka events
    asyncio.create_task(publish_kafka_event(
        topic="rex.notification.robot.emergency-stop.requested.v1",
        event_type="robot_emergency_stop_notification",
        payload={"robot_id": robot_id, "user_id": user_id}
    ))
    asyncio.create_task(publish_kafka_event(
        topic="rex.robot.emergency-stop-activated.v1",
        event_type="robot_emergency_stop_activated",
        payload={"robot_id": robot_id, "user_id": user_id}
    ))
    
    return {
        "message": "Emergency Stop activated successfully",
        "robot_id": robot_id,
        "command_id": cmd_id
    }

@router.post("/{robot_id}/emergency-stop/release", status_code=status.HTTP_202_ACCEPTED)
async def release_emergency_stop(
    robot_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Release the emergency stop, allowing robot to enter IDLE state."""
    robot = verify_robot_ownership(db, robot_id, user_id)
    
    if robot.connection_status != "ONLINE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot release emergency stop: Robot is offline"
        )
        
    cmd_id = str(uuid.uuid4())
    cmd = RobotCommand(
        id=cmd_id,
        robot_id=robot_id,
        issued_by_user_id=user_id,
        command_type="EMERGENCY_RELEASE",
        payload={"active": False},
        status="PENDING",
        priority=10,
        expires_at=utc_now_naive() + timedelta(seconds=10)
    )
    db.add(cmd)
    db.commit()
    
    # Publish MQTT QoS 1
    import asyncio
    payload = {
        "command_id": cmd_id,
        "active": False,
        "issued_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }
    asyncio.create_task(publish_mqtt_message(
        topic=f"rex/robots/{robot_id}/commands/emergency-stop",
        payload=payload,
        qos=1
    ))
    
    # Publish Kafka event
    asyncio.create_task(publish_kafka_event(
        topic="rex.robot.emergency-stop-released.v1",
        event_type="robot_emergency_stop_released",
        payload={"robot_id": robot_id, "user_id": user_id}
    ))
    
    return {
        "message": "Emergency Stop release command issued",
        "robot_id": robot_id,
        "command_id": cmd_id
    }

@router.get("/{robot_id}/commands/{command_id}", response_model=CommandResponse)
async def get_command_status(
    robot_id: str,
    command_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Query the status of a persistent high-level command."""
    verify_robot_ownership(db, robot_id, user_id)
    cmd = get_command_by_id(db, command_id)
    if not cmd or cmd.robot_id != robot_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Command not found"
        )
    return cmd
