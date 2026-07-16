import asyncio
import logging

from sqlalchemy.orm import Session

from app.config.database import SessionLocal
from app.config.redis import redis_client
from app.models.robot import Robot
from app.models.robot_event import RobotEvent
from app.services.kafka_service import publish_kafka_event
from app.services.websocket_service import broadcast_to_robot
from app.utils.dates import utc_now_naive

logger = logging.getLogger(__name__)

async def check_heartbeats():
    """Verify if active online robots have timed out and transition them offline."""
    db: Session = SessionLocal()
    try:
        now = utc_now_naive()
        online_robots = db.query(Robot).filter(Robot.connection_status == "ONLINE").all()
        
        for robot in online_robots:
            timeout_seconds = 20
            if robot.configuration:
                timeout_seconds = robot.configuration.heartbeat_timeout_seconds
                
            if robot.last_seen_at is None or (now - robot.last_seen_at).total_seconds() > timeout_seconds:
                logger.info(f"Robot {robot.id} connection timed out. Transitioning to OFFLINE.")
                robot.connection_status = "OFFLINE"
                
                # Delete Redis heartbeat key
                await redis_client.delete(f"robot:heartbeat:{robot.id}")
                
                # Revoke control lease
                await redis_client.delete(f"robot:control_lease:{robot.id}")
                
                # Log event
                db_event = RobotEvent(
                    robot_id=robot.id,
                    event_type="robot_disconnected",
                    severity="WARNING",
                    message="Robot connection timeout"
                )
                db.add(db_event)
                db.commit()
                
                # Publish Kafka notification event
                last_seen_str = robot.last_seen_at.isoformat() if robot.last_seen_at else None
                asyncio.create_task(publish_kafka_event(
                    topic="rex.notification.robot.offline.requested.v1",
                    event_type="robot_offline_notification",
                    payload={
                        "robot_id": robot.id,
                        "name": robot.name,
                        "last_seen_at": last_seen_str
                    }
                ))
                
                # Publish Kafka internal event
                asyncio.create_task(publish_kafka_event(
                    topic="rex.robot.disconnected.v1",
                    event_type="robot_disconnected",
                    payload={"robot_id": robot.id}
                ))
                
                # Notify WebSocket clients
                asyncio.create_task(broadcast_to_robot(
                    robot_id=robot.id,
                    message={
                        "type": "STATUS_UPDATE",
                        "robot_id": robot.id,
                        "connection_status": "OFFLINE",
                        "mode": robot.current_mode,
                        "emergency_stop_active": robot.emergency_stop_active,
                        "last_seen_at": last_seen_str
                    }
                ))
    except Exception as e:
        logger.error(f"Error in heartbeat monitor check: {e}")
    finally:
        db.close()

async def monitor_heartbeats_loop():
    """Background task runner for heartbeat checks."""
    logger.info("Heartbeat monitor background task started")
    while True:
        try:
            await check_heartbeats()
        except Exception as e:
            logger.error(f"Error in monitor loop iteration: {e}")
        await asyncio.sleep(5)
