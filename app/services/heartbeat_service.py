import asyncio
import logging
from typing import Mapping

from sqlalchemy.orm import Session

from app.config.database import SessionLocal
from app.config.redis import redis_client
from app.config.settings import settings
from app.models.robot import Robot
from app.models.robot_event import RobotEvent
from app.services.kafka_service import publish_kafka_event
from app.services.websocket_service import broadcast_to_robot
from app.utils.dates import utc_now_naive

logger = logging.getLogger(__name__)

def get_heartbeat_key(robot_id: str) -> str:
    return f"robot:heartbeat:{robot_id}"

async def process_heartbeat(robot_id: str, payload: dict):
    """Process a heartbeat message received from the robot device."""
    db: Session = SessionLocal()
    try:
        # Check robot exists
        robot = db.query(Robot).filter(Robot.id == robot_id).first()
        if not robot:
            logger.warning(f"Heartbeat received for unregistered robot {robot_id}")
            return
            
        now_dt = utc_now_naive()
        
        # 1. Fetch previous state from Redis
        key = get_heartbeat_key(robot_id)
        prev_heartbeat = await redis_client.hgetall(key)
        
        was_online = prev_heartbeat.get("connection_status") == "ONLINE" or robot.connection_status == "ONLINE"
        
        # 2. Update Redis live state
        heartbeat_data: Mapping[str | bytes, bytes | float | int | str] = {
            "robot_id": robot_id,
            "connection_status": "ONLINE",
            "mode": payload.get("mode", "IDLE"),
            "firmware_version": payload.get("firmware_version", ""),
            "wifi_rssi": str(payload.get("wifi_rssi", 0)),
            "uptime_seconds": str(payload.get("uptime_seconds", 0)),
            "timestamp": payload.get("timestamp", now_dt.isoformat())
        }
        
        # Config timeout or default 20s
        timeout = settings.DEFAULT_HEARTBEAT_TIMEOUT_SECONDS
        if robot.configuration:
            timeout = robot.configuration.heartbeat_timeout_seconds
            
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.hset(key, mapping=heartbeat_data)
            pipe.expire(key, timeout)
            await pipe.execute()
            
        # Update last seen on robot model
        robot.last_seen_at = now_dt
        
        # 3. Transition logic (OFFLINE -> ONLINE)
        if not was_online:
            logger.info(f"Robot {robot_id} transitioned from OFFLINE to ONLINE")
            robot.connection_status = "ONLINE"
            if payload.get("mode"):
                robot.current_mode = payload["mode"]
                
            db_event = RobotEvent(
                robot_id=robot_id,
                event_type="robot_connected",
                severity="INFO",
                message="Robot connection established (online)"
            )
            db.add(db_event)
            db.commit()
            
            # Publish Kafka connected event
            asyncio.create_task(publish_kafka_event(
                topic="rex.robot.connected.v1",
                event_type="robot_connected",
                payload={"robot_id": robot_id}
            ))
        else:
            # Sync mode changes reported by firmware if any
            reported_mode = payload.get("mode")
            if reported_mode and robot.current_mode != reported_mode:
                robot.current_mode = reported_mode
            db.commit()
            
        # 4. Notify WebSocket clients
        asyncio.create_task(broadcast_to_robot(
            robot_id=robot_id,
            message={
                "type": "STATUS_UPDATE",
                "robot_id": robot_id,
                "connection_status": "ONLINE",
                "mode": robot.current_mode,
                "emergency_stop_active": robot.emergency_stop_active,
                "firmware_version": robot.firmware_version,
                "last_seen_at": now_dt.isoformat()
            }
        ))
        
    except Exception as e:
        logger.error(f"Error processing heartbeat for robot {robot_id}: {e}")
    finally:
        db.close()
