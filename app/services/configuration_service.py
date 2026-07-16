import asyncio
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.robot import Robot
from app.models.robot_configuration import RobotConfiguration
from app.models.robot_event import RobotEvent
from app.services.kafka_service import publish_kafka_event
from app.services.mqtt_service import publish_mqtt_message
from app.utils.dates import utc_now_naive

logger = logging.getLogger(__name__)

def get_robot_configuration(db: Session, robot_id: str) -> RobotConfiguration:
    """Retrieve configuration for a robot. Raises 404 if not found."""
    config = db.query(RobotConfiguration).filter(RobotConfiguration.robot_id == robot_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    return config

def update_robot_configuration(
    db: Session, 
    robot: Robot, 
    update_data: dict
) -> RobotConfiguration:
    """Update configuration, increment version, and trigger notifications/MQTT updates."""
    config = get_robot_configuration(db, robot.id)
    
    # Update properties
    for key, value in update_data.items():
        if hasattr(config, key) and value is not None:
            setattr(config, key, value)
            
    config.version += 1
    config.updated_at = utc_now_naive()
    
    # Save event log
    db_event = RobotEvent(
        robot_id=robot.id,
        event_type="config_updated",
        severity="INFO",
        message=f"Configuration updated to version {config.version}"
    )
    db.add(db_event)
    db.commit()
    db.refresh(config)
    
    # Convert config properties to dict for MQTT payload
    config_dict = {
        "version": config.version,
        "base_max_speed": config.base_max_speed,
        "base_default_speed": config.base_default_speed,
        "turn_speed": config.turn_speed,
        "acceleration_step": config.acceleration_step,
        "braking_step": config.braking_step,
        "joystick_dead_zone": config.joystick_dead_zone,
        "joystick_timeout_ms": config.joystick_timeout_ms,
        "obstacle_stop_distance_cm": config.obstacle_stop_distance_cm,
        "arm_base_min_angle": config.arm_base_min_angle,
        "arm_base_max_angle": config.arm_base_max_angle,
        "arm_shoulder_min_angle": config.arm_shoulder_min_angle,
        "arm_shoulder_max_angle": config.arm_shoulder_max_angle,
        "arm_elbow_min_angle": config.arm_elbow_min_angle,
        "arm_elbow_max_angle": config.arm_elbow_max_angle,
        "arm_grip_min_angle": config.arm_grip_min_angle,
        "arm_grip_max_angle": config.arm_grip_max_angle,
        "arm_default_speed": config.arm_default_speed,
        "heartbeat_interval_seconds": config.heartbeat_interval_seconds,
        "heartbeat_timeout_seconds": config.heartbeat_timeout_seconds,
        "telemetry_interval_ms": config.telemetry_interval_ms,
        "buzzer_enabled": config.buzzer_enabled,
        "oled_eyes_enabled": config.oled_eyes_enabled,
        "automatic_night_light": config.automatic_night_light
    }
    
    # 1. Publish to MQTT command config topic
    asyncio.create_task(publish_mqtt_message(
        topic=f"rex/robots/{robot.id}/commands/config",
        payload=config_dict
    ))
    
    # 2. Publish internal Kafka event
    asyncio.create_task(publish_kafka_event(
        topic="rex.robot.config-updated.v1",
        event_type="robot_config_updated",
        payload={
            "robot_id": robot.id,
            "version": config.version,
            "configuration": config_dict
        }
    ))
    
    # 3. WebSocket broadcasts are done via the WebSocket Connection Manager (WebsocketService)
    # which will be imported or injected in the route layer or websocket_service.py.
    from app.services.websocket_service import broadcast_to_robot
    asyncio.create_task(broadcast_to_robot(
        robot_id=robot.id,
        message={"type": "CONFIG_UPDATE", "version": config.version, "config": config_dict}
    ))
    
    return config
