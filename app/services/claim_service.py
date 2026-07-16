import asyncio
import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config.redis import redis_client
from app.models.device_session import RobotDeviceSession
from app.models.robot import Robot
from app.models.robot_event import RobotEvent
from app.services.control_lease_service import get_lease_key
from app.services.kafka_service import publish_kafka_event
from app.services.mqtt_service import publish_mqtt_message
from app.utils.dates import utc_now_naive
from app.utils.secrets import generate_random_secret, hash_secret, verify_secret

logger = logging.getLogger(__name__)

def claim_robot(db: Session, robot_id: str, robot_secret: str, user_id: str) -> Robot:
    """Claim an unclaimed robot using its ID and secret."""
    # Find the robot
    robot = db.query(Robot).filter(Robot.id == robot_id).first()
    if not robot:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to claim robot"
        )
        
    # Check if already claimed
    if robot.status != "UNCLAIMED" or robot.owner_user_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to claim robot"
        )
        
    # Verify secret
    if not verify_secret(robot.device_secret_hash, robot_secret):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to claim robot"
        )
        
    # Process claim
    robot.owner_user_id = user_id
    robot.status = "CLAIMED"
    robot.claimed_at = utc_now_naive()
    robot.updated_at = utc_now_naive()
    
    # Log event
    db_event = RobotEvent(
        robot_id=robot.id,
        event_type="robot_claimed",
        severity="INFO",
        message=f"Robot claimed successfully by user {user_id}"
    )
    db.add(db_event)
    db.commit()
    db.refresh(robot)
    
    # Publish events
    asyncio.create_task(publish_kafka_event(
        topic="rex.notification.robot.claimed.requested.v1",
        event_type="robot_claimed_notification",
        payload={
            "user_id": user_id,
            "robot": {"id": robot.id, "name": robot.name}
        }
    ))
    
    asyncio.create_task(publish_kafka_event(
        topic="rex.robot.claimed.v1",
        event_type="robot_claimed",
        payload={
            "user_id": user_id,
            "robot": {"id": robot.id, "name": robot.name}
        }
    ))
    
    return robot

def unpair_robot(db: Session, robot: Robot) -> Robot:
    """Unpair the robot, revoke sessions, reset state, and notify."""
    robot_id = robot.id
    user_id = robot.owner_user_id
    
    # 1. Reset ownership and state
    robot.owner_user_id = None
    robot.status = "UNCLAIMED"
    robot.current_mode = "IDLE"
    robot.emergency_stop_active = True  # Put into e-stop until safe reconnect
    robot.secret_rotation_required = True
    
    # 2. Rotate credentials
    new_raw_secret = generate_random_secret()
    robot.device_secret_hash = hash_secret(new_raw_secret)
    robot.updated_at = utc_now_naive()
    
    # 3. Revoke all active device sessions
    db.query(RobotDeviceSession).filter(
        RobotDeviceSession.robot_id == robot_id,
        RobotDeviceSession.revoked_at.is_(None)
    ).update({
        "revoked_at": utc_now_naive()
    }, synchronize_session=False)
    
    # 4. Log event
    db_event = RobotEvent(
        robot_id=robot_id,
        event_type="robot_unpaired",
        severity="WARNING",
        message=f"Robot unpaired by user {user_id}"
    )
    db.add(db_event)
    db.commit()
    db.refresh(robot)
    
    # 5. Clear Redis Control Lease and active state
    async def clear_redis_and_send_estop():
        key = get_lease_key(robot_id)
        await redis_client.delete(key)
        
        # Publish MQTT E-Stop QoS 1
        import uuid
        command_id = str(uuid.uuid4())
        payload = {
            "command_id": command_id,
            "active": True,
            "reason": "USER_UNPAIR",
            "issued_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        await publish_mqtt_message(
            topic=f"rex/robots/{robot_id}/commands/emergency-stop",
            payload=payload,
            qos=1
        )
        
    asyncio.create_task(clear_redis_and_send_estop())
    
    # 6. Publish Kafka notification and event
    asyncio.create_task(publish_kafka_event(
        topic="rex.notification.robot.unpaired.requested.v1",
        event_type="robot_unpaired_notification",
        payload={
            "user_id": user_id,
            "robot": {"id": robot_id, "name": robot.name}
        }
    ))
    
    asyncio.create_task(publish_kafka_event(
        topic="rex.robot.unpaired.v1",
        event_type="robot_unpaired",
        payload={
            "user_id": user_id,
            "robot": {"id": robot_id, "name": robot.name}
        }
    ))
    
    return robot
