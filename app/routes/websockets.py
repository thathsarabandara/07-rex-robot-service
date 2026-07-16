import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Mapping

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.config.database import SessionLocal
from app.config.redis import redis_client
from app.models.robot import Robot
from app.models.robot_event import RobotEvent
from app.schemas.websocket import (
    ArmJointMessage,
    ArmPoseMessage,
    BaseDirectionMessage,
    BaseJoystickMessage,
    SpeedUpdateMessage,
)
from app.services.control_lease_service import (
    acquire_control_lease,
    get_control_lease_status,
    release_control_lease,
)
from app.services.mqtt_service import publish_mqtt_message
from app.services.websocket_service import manager
from app.utils.command_ids import generate_command_id
from app.utils.tokens import decode_user_jwt
from app.utils.validation import apply_joystick_deadzone, clamp_speed, validate_joint_angle

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws/robots", tags=["WebSockets"])

async def authenticate_ws(websocket: WebSocket, robot_id: str, token: str | None) -> tuple[str, Robot] | None:
    """Validate token and verify user ownership of the robot. Closes socket if invalid."""
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token is required")
        return None
        
    payload = decode_user_jwt(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return None
        
    user_id = payload["sub"]
    
    db: Session = SessionLocal()
    try:
        robot = db.query(Robot).filter(Robot.id == robot_id).first()
        if not robot:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Robot not found")
            return None
        if robot.status != "CLAIMED":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Robot is not claimed")
            return None
        if robot.owner_user_id != user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Robot ownership mismatch")
            return None
            
        # Log WS connection event
        db_event = RobotEvent(
            robot_id=robot_id,
            event_type="client_connected",
            severity="INFO",
            message=f"WebSocket client connected. User: {user_id}"
        )
        db.add(db_event)
        db.commit()
        
        # Detach from session to avoid thread issues, but keep object info
        db.expunge(robot)
        return user_id, robot
    except Exception as e:
        logger.error(f"WS Authentication error: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal error")
        return None
    finally:
        db.close()

async def handle_ws_disconnect(robot_id: str, user_id: str, connection_id: str):
    """Release control lease, send halt command if needed, and log event on disconnect."""
    # Check if this connection holds the active control lease
    lease = await get_control_lease_status(robot_id)
    if lease and lease.get("connection_id") == connection_id:
        logger.info(f"Releasing active control lease for robot {robot_id} on WebSocket disconnect.")
        await release_control_lease(robot_id, user_id, connection_id)
        
        # Publish STOP command
        cmd_id = generate_command_id()
        now = datetime.now(timezone.utc)
        stop_payload = {
            "command_id": cmd_id,
            "type": "BASE_JOYSTICK",
            "sequence": 99999,
            "x": 0.0,
            "y": 0.0,
            "speed_limit": 0,
            "issued_at": now.isoformat().replace("+00:00", "Z"),
            "expires_at": (now + timedelta(milliseconds=500)).isoformat().replace("+00:00", "Z")
        }
        await publish_mqtt_message(
            topic=f"rex/robots/{robot_id}/commands/base",
            payload=stop_payload
        )
        
    db = SessionLocal()
    try:
        db_event = RobotEvent(
            robot_id=robot_id,
            event_type="client_disconnected",
            severity="INFO",
            message=f"WebSocket client disconnected. User: {user_id}"
        )
        db.add(db_event)
        db.commit()
    except Exception as e:
        logger.error(f"Error logging disconnect event: {e}")
    finally:
        db.close()

# ----------------- Control WS Channel -----------------
@router.websocket("/{robot_id}/control")
async def ws_control(
    websocket: WebSocket,
    robot_id: str,
    token: str | None = Query(None)
):
    auth = await authenticate_ws(websocket, robot_id, token)
    if not auth:
        return
        
    user_id, robot = auth
    connection_id = str(uuid.uuid4())
    
    await manager.connect(robot_id, websocket)
    
    # Send Initial State
    db = SessionLocal()
    db_robot = db.query(Robot).filter(Robot.id == robot_id).first()
    if not db_robot:
        db.close()
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Robot not found")
        return
    config_ver = db_robot.configuration.version if db_robot.configuration else 1
    connection_status = db_robot.connection_status
    current_mode = db_robot.current_mode
    emergency_stop_active = db_robot.emergency_stop_active
    db.close()
    
    await websocket.send_json({
        "type": "INITIAL_STATE",
        "connection_status": connection_status,
        "mode": current_mode,
        "emergency_stop_active": emergency_stop_active,
        "config_version": config_ver
    })
    
    # Last processed sequence logic to discard stale sequence numbers
    last_seq = 0
    
    try:
        while True:
            data_str = await websocket.receive_text()
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON format"})
                continue
                
            msg_type = data.get("type")
            if not msg_type:
                await websocket.send_json({"error": "Missing message type"})
                continue
                
            # Fetch fresh robot state to enforce safety triggers
            db = SessionLocal()
            fresh_robot = db.query(Robot).filter(Robot.id == robot_id).first()
            if not fresh_robot:
                db.close()
                await websocket.send_json({"error": "Robot not found"})
                break
            
            # Enforce Emergency Stop check
            if fresh_robot.emergency_stop_active or fresh_robot.current_mode == "EMERGENCY_STOP":
                db.close()
                await websocket.send_json({"error": "Command rejected: Robot in Emergency Stop mode"})
                continue
                
            # Enforce Offline check
            if fresh_robot.connection_status != "ONLINE":
                db.close()
                await websocket.send_json({"error": "Command rejected: Robot is offline"})
                continue
                
            # Enforce Control Lease check
            lease = await get_control_lease_status(robot_id)
            print("DEBUG: connection_id=", connection_id, "lease=", lease)
            if not lease or lease.get("connection_id") != connection_id:
                db.close()
                await websocket.send_json({"error": "Command rejected: Active lease not held by this connection"})
                continue
                
            # Renew control lease TTL automatically upon command activity
            await acquire_control_lease(robot_id, user_id, connection_id, lease.get("control_channel", "WEB"))
            
            config = fresh_robot.configuration
            
            # Process BASE_JOYSTICK
            if msg_type == "BASE_JOYSTICK":
                try:
                    joystick_msg = BaseJoystickMessage.model_validate(data)
                except Exception as ve:
                    db.close()
                    await websocket.send_json({"error": f"Validation failed: {ve}"})
                    continue
                    
                # Ignore stale sequences
                if joystick_msg.sequence <= last_seq:
                    db.close()
                    continue
                last_seq = joystick_msg.sequence
                
                # Apply dead zone & speed clamps
                x = apply_joystick_deadzone(joystick_msg.x, config.joystick_dead_zone)
                y = apply_joystick_deadzone(joystick_msg.y, config.joystick_dead_zone)
                speed_limit = clamp_speed(joystick_msg.speed_limit, config.base_max_speed)
                
                # Publish MQTT payload
                cmd_id = generate_command_id()
                now = datetime.now(timezone.utc)
                mqtt_payload = {
                    "command_id": cmd_id,
                    "type": "BASE_JOYSTICK",
                    "sequence": joystick_msg.sequence,
                    "x": x,
                    "y": y,
                    "speed_limit": speed_limit,
                    "issued_at": now.isoformat().replace("+00:00", "Z"),
                    "expires_at": (now + timedelta(milliseconds=config.joystick_timeout_ms)).isoformat().replace("+00:00", "Z")
                }
                await publish_mqtt_message(
                    topic=f"rex/robots/{robot_id}/commands/base",
                    payload=mqtt_payload
                )
                
            # Process BASE_DIRECTION
            elif msg_type == "BASE_DIRECTION":
                try:
                    dir_msg = BaseDirectionMessage.model_validate(data)
                except Exception as ve:
                    db.close()
                    await websocket.send_json({"error": f"Validation failed: {ve}"})
                    continue
                    
                speed = clamp_speed(dir_msg.speed, config.base_max_speed)
                
                cmd_id = generate_command_id()
                now = datetime.now(timezone.utc)
                mqtt_payload = {
                    "command_id": cmd_id,
                    "type": "BASE_DIRECTION",
                    "direction": dir_msg.direction,
                    "speed": speed,
                    "duration_ms": dir_msg.duration_ms,
                    "issued_at": now.isoformat().replace("+00:00", "Z")
                }
                await publish_mqtt_message(
                    topic=f"rex/robots/{robot_id}/commands/base",
                    payload=mqtt_payload
                )
                
            # Process SPEED_UPDATE
            elif msg_type == "SPEED_UPDATE":
                try:
                    speed_msg = SpeedUpdateMessage.model_validate(data)
                except Exception as ve:
                    db.close()
                    await websocket.send_json({"error": f"Validation failed: {ve}"})
                    continue
                    
                # Cache speeds in Redis
                speeds_data: Mapping[str | bytes, bytes | float | int | str] = {
                    "base_speed_limit": str(clamp_speed(speed_msg.base_speed_limit, config.base_max_speed)),
                    "turn_speed": str(clamp_speed(speed_msg.turn_speed, config.base_max_speed)),
                    "arm_speed": str(clamp_speed(speed_msg.arm_speed, config.base_max_speed))
                }
                await redis_client.hset(f"robot:speeds:{robot_id}", mapping=speeds_data)
                
                # Publish config speeds update MQTT
                cmd_id = generate_command_id()
                await publish_mqtt_message(
                    topic=f"rex/robots/{robot_id}/commands/config",
                    payload={
                        "command_id": cmd_id,
                        "speeds": speeds_data
                    }
                )
                
                # Confirm back to client
                await websocket.send_json({
                    "type": "SPEED_CONFIRM",
                    "base_speed_limit": int(speeds_data["base_speed_limit"]),
                    "turn_speed": int(speeds_data["turn_speed"]),
                    "arm_speed": int(speeds_data["arm_speed"])
                })
                
            else:
                await websocket.send_json({"error": f"Unsupported message type: {msg_type}"})
                
            db.close()
            
    except WebSocketDisconnect:
        manager.disconnect(robot_id, websocket)
        await handle_ws_disconnect(robot_id, user_id, connection_id)
    except Exception as e:
        logger.error(f"WS control loop error: {e}")
        manager.disconnect(robot_id, websocket)
        await handle_ws_disconnect(robot_id, user_id, connection_id)

# ----------------- Arm WS Channel -----------------
@router.websocket("/{robot_id}/arm")
async def ws_arm(
    websocket: WebSocket,
    robot_id: str,
    token: str | None = Query(None)
):
    auth = await authenticate_ws(websocket, robot_id, token)
    if not auth:
        return
        
    user_id, robot = auth
    f"arm_conn_{id(websocket)}"
    
    await manager.connect(robot_id, websocket)
    last_seq = 0
    
    try:
        while True:
            data_str = await websocket.receive_text()
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON format"})
                continue
                
            msg_type = data.get("type")
            if not msg_type:
                await websocket.send_json({"error": "Missing message type"})
                continue
                
            # Fetch fresh robot state
            db = SessionLocal()
            fresh_robot = db.query(Robot).filter(Robot.id == robot_id).first()
            if not fresh_robot:
                db.close()
                await websocket.send_json({"error": "Robot not found"})
                break
                
            if fresh_robot.emergency_stop_active or fresh_robot.current_mode == "EMERGENCY_STOP":
                db.close()
                await websocket.send_json({"error": "Command rejected: Robot in Emergency Stop mode"})
                continue
                
            if fresh_robot.connection_status != "ONLINE":
                db.close()
                await websocket.send_json({"error": "Command rejected: Robot is offline"})
                continue
                
            config = fresh_robot.configuration
            
            # ARM_JOINT control
            if msg_type == "ARM_JOINT":
                try:
                    arm_joint_msg = ArmJointMessage.model_validate(data)
                except Exception as ve:
                    db.close()
                    await websocket.send_json({"error": f"Validation failed: {ve}"})
                    continue
                    
                if arm_joint_msg.sequence <= last_seq:
                    db.close()
                    continue
                last_seq = arm_joint_msg.sequence
                
                # Clamp joint angles
                clamped_angle = validate_joint_angle(arm_joint_msg.joint, arm_joint_msg.angle, config)
                speed = clamp_speed(arm_joint_msg.speed, config.arm_default_speed)
                
                cmd_id = generate_command_id()
                now = datetime.now(timezone.utc)
                mqtt_payload = {
                    "command_id": cmd_id,
                    "type": "ARM_JOINT",
                    "joint": arm_joint_msg.joint,
                    "angle": clamped_angle,
                    "speed": speed,
                    "sequence": arm_joint_msg.sequence,
                    "issued_at": now.isoformat().replace("+00:00", "Z"),
                    "expires_at": (now + timedelta(seconds=2)).isoformat().replace("+00:00", "Z")
                }
                await publish_mqtt_message(
                    topic=f"rex/robots/{robot_id}/commands/arm",
                    payload=mqtt_payload
                )
                
            # ARM_POSE control
            elif msg_type == "ARM_POSE":
                try:
                    arm_pose_msg = ArmPoseMessage.model_validate(data)
                except Exception as ve:
                    db.close()
                    await websocket.send_json({"error": f"Validation failed: {ve}"})
                    continue
                    
                if arm_pose_msg.sequence <= last_seq:
                    db.close()
                    continue
                last_seq = arm_pose_msg.sequence
                
                # Clamp all pose joint angles
                clamped_pose = {
                    "base": validate_joint_angle("BASE", arm_pose_msg.joints.base, config),
                    "shoulder": validate_joint_angle("SHOULDER", arm_pose_msg.joints.shoulder, config),
                    "elbow": validate_joint_angle("ELBOW", arm_pose_msg.joints.elbow, config),
                    "grip": validate_joint_angle("GRIP", arm_pose_msg.joints.grip, config)
                }
                speed = clamp_speed(arm_pose_msg.speed, config.arm_default_speed)
                
                cmd_id = generate_command_id()
                now = datetime.now(timezone.utc)
                mqtt_payload = {
                    "command_id": cmd_id,
                    "type": "ARM_POSE",
                    "joints": clamped_pose,
                    "speed": speed,
                    "sequence": arm_pose_msg.sequence,
                    "issued_at": now.isoformat().replace("+00:00", "Z"),
                    "expires_at": (now + timedelta(seconds=2)).isoformat().replace("+00:00", "Z")
                }
                await publish_mqtt_message(
                    topic=f"rex/robots/{robot_id}/commands/arm",
                    payload=mqtt_payload
                )
                
            # ARM_STOP control
            elif msg_type == "ARM_STOP":
                cmd_id = generate_command_id()
                now = datetime.now(timezone.utc)
                mqtt_payload = {
                    "command_id": cmd_id,
                    "type": "ARM_STOP",
                    "issued_at": now.isoformat().replace("+00:00", "Z")
                }
                await publish_mqtt_message(
                    topic=f"rex/robots/{robot_id}/commands/arm",
                    payload=mqtt_payload
                )
                
            else:
                await websocket.send_json({"error": f"Unsupported message type: {msg_type}"})
                
            db.close()
            
    except WebSocketDisconnect:
        manager.disconnect(robot_id, websocket)
    except Exception as e:
        logger.error(f"WS arm loop error: {e}")
        manager.disconnect(robot_id, websocket)

# ----------------- Status WS Channel (Read-Only) -----------------
@router.websocket("/{robot_id}/status")
async def ws_status(
    websocket: WebSocket,
    robot_id: str,
    token: str | None = Query(None)
):
    auth = await authenticate_ws(websocket, robot_id, token)
    if not auth:
        return
        
    user_id, robot = auth
    await manager.connect(robot_id, websocket)
    
    # Broadcast current status immediately
    db = SessionLocal()
    db_robot = db.query(Robot).filter(Robot.id == robot_id).first()
    if not db_robot:
        db.close()
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Robot not found")
        return
    connection_status = db_robot.connection_status
    current_mode = db_robot.current_mode
    emergency_stop_active = db_robot.emergency_stop_active
    last_seen_str = db_robot.last_seen_at.isoformat() if db_robot.last_seen_at else None
    db.close()
    
    await websocket.send_json({
        "type": "STATUS_UPDATE",
        "robot_id": robot_id,
        "connection_status": connection_status,
        "mode": current_mode,
        "emergency_stop_active": emergency_stop_active,
        "last_seen_at": last_seen_str
    })
    
    try:
        while True:
            # Maintain active channel open, discard any input from client
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(robot_id, websocket)
    except Exception:
        manager.disconnect(robot_id, websocket)
