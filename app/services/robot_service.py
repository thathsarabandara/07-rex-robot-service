import logging
import re
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.robot import Robot
from app.models.robot_configuration import RobotConfiguration
from app.models.robot_event import RobotEvent
from app.services.kafka_service import publish_kafka_event
from app.utils.dates import utc_now_naive
from app.utils.secrets import generate_random_secret, hash_secret

logger = logging.getLogger(__name__)

SERIAL_REGEX = re.compile(r"^REX-[A-Z0-9]+-[0-9]+$")

def validate_serial_number(serial: str):
    """Validate that the serial number matches REX-[A-Z0-9]+-[0-9]+."""
    if not SERIAL_REGEX.match(serial):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid serial number format. Must match 'REX-[MODEL]-[NUMBER]'"
        )

def register_robot(db: Session, serial_number: str, hardware_model: str, name: str) -> tuple[Robot, str]:
    """Register/provision a new physical robot with a unique serial number."""
    validate_serial_number(serial_number)
    
    # Check if serial number already exists
    existing = db.query(Robot).filter(Robot.serial_number == serial_number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Serial number already registered"
        )
        
    robot_id = str(uuid.uuid4())
    raw_secret = generate_random_secret()
    secret_hash = hash_secret(raw_secret)
    
    db_robot = Robot(
        id=robot_id,
        serial_number=serial_number,
        hardware_model=hardware_model,
        name=name,
        device_secret_hash=secret_hash,
        status="UNCLAIMED",
        connection_status="OFFLINE",
        current_mode="IDLE"
    )
    db.add(db_robot)
    
    # Create default configuration
    db_config = RobotConfiguration(
        robot_id=robot_id,
        version=1,
        base_max_speed=100,
        base_default_speed=50,
        turn_speed=50,
        acceleration_step=5,
        braking_step=10,
        joystick_dead_zone=0.05,
        joystick_timeout_ms=500,
        obstacle_stop_distance_cm=20,
        arm_base_min_angle=0,
        arm_base_max_angle=180,
        arm_shoulder_min_angle=0,
        arm_shoulder_max_angle=180,
        arm_elbow_min_angle=0,
        arm_elbow_max_angle=180,
        arm_grip_min_angle=0,
        arm_grip_max_angle=180,
        arm_default_speed=50,
        heartbeat_interval_seconds=5,
        heartbeat_timeout_seconds=20,
        telemetry_interval_ms=1000,
        buzzer_enabled=True,
        oled_eyes_enabled=True,
        automatic_night_light=True
    )
    db.add(db_config)
    
    # Log event
    db_event = RobotEvent(
        robot_id=robot_id,
        event_type="robot_registered",
        severity="INFO",
        message=f"Robot registered successfully with serial: {serial_number}"
    )
    db.add(db_event)
    
    db.commit()
    db.refresh(db_robot)
    
    # Publish Kafka event
    # Need to run in background or execute asynchronously
    import asyncio
    asyncio.create_task(publish_kafka_event(
        topic="rex.robot.registered.v1",
        event_type="robot_registered",
        payload={
            "robot": {
                "id": db_robot.id,
                "serial_number": db_robot.serial_number,
                "status": db_robot.status
            }
        }
    ))
    
    return db_robot, raw_secret

def get_robot_by_id(db: Session, robot_id: str) -> Robot | None:
    return db.query(Robot).filter(Robot.id == robot_id).first()

def get_user_robots(db: Session, user_id: str) -> list[Robot]:
    return db.query(Robot).filter(Robot.owner_user_id == user_id).all()

def update_robot_profile(db: Session, robot: Robot, name: str | None, description: str | None, location_label: str | None) -> Robot:
    if name is not None:
        robot.name = name
    if description is not None:
        robot.description = description
    if location_label is not None:
        robot.location_label = location_label
        
    robot.updated_at = utc_now_naive()
    db.commit()
    db.refresh(robot)
    return robot
