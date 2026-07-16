import asyncio
import json
import logging

from app.config.database import SessionLocal
from app.config.settings import settings
from app.models.robot_event import RobotEvent
from app.services.command_service import update_command_status
from app.services.heartbeat_service import process_heartbeat
from app.services.kafka_service import publish_kafka_event
from app.services.websocket_service import broadcast_to_robot

logger = logging.getLogger(__name__)

async def handle_mqtt_message(topic: str, payload_str: str):
    """Parse, route, and action incoming MQTT topic payloads."""
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        logger.warning(f"MQTT message payload on {topic} is not JSON: {payload_str}")
        return
        
    parts = topic.split("/")
    if len(parts) < 4:
        return
    robot_id = parts[2]
    topic_type = parts[3]
    
    if topic_type == "heartbeat":
        await process_heartbeat(robot_id, payload)
    elif topic_type == "status":
        await broadcast_to_robot(robot_id, {
            "type": "STATUS_UPDATE",
            "robot_id": robot_id,
            **payload
        })
    elif topic_type == "acknowledgements":
        command_id = payload.get("command_id")
        ack_status = payload.get("status")
        db = SessionLocal()
        try:
            if command_id and ack_status:
                reason = payload.get("message") or payload.get("failure_reason")
                update_command_status(db, command_id, ack_status, failure_reason=reason)
                
                if ack_status in ("FAILED", "REJECTED"):
                    asyncio.create_task(publish_kafka_event(
                        topic="rex.notification.robot.command-failed.requested.v1",
                        event_type="robot_command_failed_notification",
                        payload={"robot_id": robot_id, "command_id": command_id, "status": ack_status, "reason": reason}
                    ))
                    asyncio.create_task(publish_kafka_event(
                        topic="rex.robot.command-failed.v1",
                        event_type="robot_command_failed",
                        payload={"robot_id": robot_id, "command_id": command_id, "status": ack_status, "reason": reason}
                    ))
        except Exception as e:
            logger.error(f"Error updating database ack: {e}")
        finally:
            db.close()
            
        await broadcast_to_robot(robot_id, {
            "type": "COMMAND_ACK",
            "robot_id": robot_id,
            **payload
        })
    elif topic_type == "events":
        db = SessionLocal()
        try:
            event_type = payload.get("event_type", "device_event")
            severity = payload.get("severity", "INFO")
            message = payload.get("message", "")
            meta = payload.get("metadata")
            
            db_event = RobotEvent(
                robot_id=robot_id,
                event_type=event_type,
                severity=severity,
                message=message,
                metadata_json=meta
            )
            db.add(db_event)
            db.commit()
        except Exception as e:
            logger.error(f"Error logging device event: {e}")
        finally:
            db.close()
            
        await broadcast_to_robot(robot_id, {
            "type": "DEVICE_EVENT",
            "robot_id": robot_id,
            **payload
        })

async def run_mqtt_consumer():
    """Start the background MQTT consumer loop subscribing to status, heartbeat, events, and acks."""
    if settings.APP_ENV == "test":
        logger.info("Skipping MQTT consumer in test environment")
        return
        
    import aiomqtt
    while True:
        try:
            async with aiomqtt.Client(
                hostname=settings.MQTT_HOST,
                port=settings.MQTT_PORT,
                username=settings.MQTT_USERNAME,
                password=settings.MQTT_PASSWORD,
                timeout=settings.MQTT_KEEPALIVE_SECONDS
            ) as client:
                logger.info("MQTT consumer subscribed to topic channels successfully")
                await client.subscribe("rex/robots/+/heartbeat")
                await client.subscribe("rex/robots/+/status")
                await client.subscribe("rex/robots/+/acknowledgements")
                await client.subscribe("rex/robots/+/events")
                
                async for message in client.messages:
                    topic = str(message.topic)
                    payload_str = message.payload.decode("utf-8")
                    await handle_mqtt_message(topic, payload_str)
                    
        except aiomqtt.MqttError as e:
            logger.error(f"MQTT Consumer connection error: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"MQTT Consumer unhandled exception: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
