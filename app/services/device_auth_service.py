import asyncio
import hashlib
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.device_session import RobotDeviceSession
from app.models.robot import Robot
from app.models.robot_event import RobotEvent
from app.services.kafka_service import publish_kafka_event
from app.utils.dates import utc_now_naive
from app.utils.secrets import verify_secret
from app.utils.tokens import create_robot_tokens, decode_robot_jwt

logger = logging.getLogger(__name__)

def hash_token(token: str) -> str:
    """Hash token for storage in MySQL database using SHA256."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def authenticate_device(
    db: Session, 
    robot_id: str, 
    robot_secret: str, 
    firmware_version: str | None, 
    ip_address: str | None
) -> dict:
    """Authenticate robot device, create session, and return tokens."""
    robot = db.query(Robot).filter(Robot.id == robot_id).first()
    if not robot:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid robot credentials"
        )
        
    if robot.status == "DISABLED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Robot is disabled"
        )
        
    if not verify_secret(robot.device_secret_hash, robot_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid robot credentials"
        )
        
    # Generate tokens
    access_token, refresh_token, access_exp, refresh_exp = create_robot_tokens(robot.id)
    
    # Store session
    session = RobotDeviceSession(
        robot_id=robot.id,
        refresh_token_hash=hash_token(refresh_token),
        ip_address=ip_address,
        firmware_version=firmware_version,
        access_expires_at=access_exp,
        refresh_expires_at=refresh_exp
    )
    db.add(session)
    
    # Update firmware version on robot model
    if firmware_version:
        robot.firmware_version = firmware_version
        
    # Log event
    db_event = RobotEvent(
        robot_id=robot.id,
        event_type="robot_authenticated",
        severity="INFO",
        message=f"Robot authenticated successfully from IP: {ip_address}"
    )
    db.add(db_event)
    db.commit()
    
    # Publish Kafka event
    asyncio.create_task(publish_kafka_event(
        topic="rex.robot.authenticated.v1",
        event_type="robot_authenticated",
        payload={
            "robot": {
                "id": robot.id,
                "serial_number": robot.serial_number,
                "firmware_version": firmware_version
            }
        }
    ))
    
    # Return auth structure
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "access_token_expires_in": settings.ROBOT_ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        "refresh_token_expires_in": settings.ROBOT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        "mqtt": {
            "host": settings.MQTT_HOST,
            "port": settings.MQTT_PORT,
            "tls": settings.MQTT_TLS_ENABLED,
            "client_id": f"rex-robot-{robot.id}"
        }
    }

def refresh_device_token(db: Session, refresh_token: str, ip_address: str | None) -> dict:
    """Refresh robot tokens using valid refresh token."""
    payload = decode_robot_jwt(refresh_token, expected_type="robot_refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
        
    robot_id = payload["sub"]
    token_hash = hash_token(refresh_token)
    
    # Find session
    session = db.query(RobotDeviceSession).filter(
        RobotDeviceSession.robot_id == robot_id,
        RobotDeviceSession.refresh_token_hash == token_hash,
        RobotDeviceSession.revoked_at.is_(None)
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found or revoked"
        )
        
    if session.refresh_expires_at < utc_now_naive():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired"
        )
        
    # Check robot status
    robot = db.query(Robot).filter(Robot.id == robot_id).first()
    if not robot or robot.status == "DISABLED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Robot is disabled or not found"
        )
        
    # Revoke old session
    session.revoked_at = utc_now_naive()
    
    # Generate new tokens
    access_token, new_refresh_token, access_exp, refresh_exp = create_robot_tokens(robot_id)
    
    # Create new session
    new_session = RobotDeviceSession(
        robot_id=robot_id,
        refresh_token_hash=hash_token(new_refresh_token),
        ip_address=ip_address,
        firmware_version=session.firmware_version,
        access_expires_at=access_exp,
        refresh_expires_at=refresh_exp
    )
    db.add(new_session)
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "Bearer",
        "access_token_expires_in": settings.ROBOT_ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        "refresh_token_expires_in": settings.ROBOT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        "mqtt": {
            "host": settings.MQTT_HOST,
            "port": settings.MQTT_PORT,
            "tls": settings.MQTT_TLS_ENABLED,
            "client_id": f"rex-robot-{robot_id}"
        }
    }

def revoke_device_session(db: Session, robot_id: str):
    """Revoke all device sessions for a robot."""
    db.query(RobotDeviceSession).filter(
        RobotDeviceSession.robot_id == robot_id,
        RobotDeviceSession.revoked_at.is_(None)
    ).update({
        "revoked_at": utc_now_naive()
    }, synchronize_session=False)
    db.commit()
