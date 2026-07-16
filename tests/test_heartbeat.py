from datetime import datetime, timedelta, timezone
import asyncio
import pytest

from app.models.robot import Robot
from app.models.robot_event import RobotEvent
from app.services.heartbeat_service import process_heartbeat
from app.services.kafka_service import test_events
from app.workers.heartbeat_monitor import check_heartbeats


@pytest.mark.asyncio
async def test_process_heartbeat_offline_to_online(generate_user_jwt, db, mock_redis):
    # Setup robot
    db_robot = Robot(
        id="robot-123",
        serial_number="REX-ESP32-9999",
        hardware_model="REX-47",
        name="REX-47",
        device_secret_hash="hash",
        status="CLAIMED",
        connection_status="OFFLINE",
        current_mode="IDLE"
    )
    db.add(db_robot)
    db.commit()
    
    test_events.clear()
    
    # Process heartbeat
    payload = {
        "mode": "MANUAL",
        "firmware_version": "1.2.0",
        "wifi_rssi": -60,
        "uptime_seconds": 120,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await process_heartbeat("robot-123", payload)
    await asyncio.sleep(0.1)
    
    # Verify Redis live state cache
    redis_key = "robot:heartbeat:robot-123"
    assert redis_key in mock_redis.store
    assert mock_redis.store[redis_key]["connection_status"] == "ONLINE"
    assert mock_redis.store[redis_key]["mode"] == "MANUAL"
    
    # Verify DB transition to ONLINE
    db.expire_all()
    robot = db.query(Robot).filter(Robot.id == "robot-123").first()
    assert robot.connection_status == "ONLINE"
    assert robot.current_mode == "MANUAL"
    assert robot.last_seen_at is not None
    
    # Verify event logged
    events = db.query(RobotEvent).filter(RobotEvent.robot_id == "robot-123").all()
    assert len(events) == 1
    assert events[0].event_type == "robot_connected"
    
    # Verify Kafka connected event
    assert len(test_events) == 1
    assert test_events[0][0] == "rex.robot.connected.v1"

@pytest.mark.asyncio
async def test_heartbeat_monitor_expiry(db, mock_redis):
    # Setup online robot with old last_seen_at
    old_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=30)
    db_robot = Robot(
        id="robot-123",
        serial_number="REX-ESP32-9999",
        hardware_model="REX-47",
        name="REX-47",
        device_secret_hash="hash",
        status="CLAIMED",
        connection_status="ONLINE",
        current_mode="MANUAL",
        last_seen_at=old_time
    )
    db.add(db_robot)
    db.commit()
    
    # Setup configurations (with 20s timeout)
    from app.models.robot_configuration import RobotConfiguration
    db_config = RobotConfiguration(
        robot_id="robot-123",
        heartbeat_timeout_seconds=20
    )
    db.add(db_config)
    db.commit()
    
    # Populate Redis lease and heartbeat to test deletions
    mock_redis.store["robot:heartbeat:robot-123"] = {"connection_status": "ONLINE"}
    mock_redis.store["robot:control_lease:robot-123"] = {"connection_id": "conn-1"}
    
    test_events.clear()
    
    # Run monitor check
    await check_heartbeats()
    await asyncio.sleep(0.1)
    
    # Verify DB transition to OFFLINE
    db.expire_all()
    robot = db.query(Robot).filter(Robot.id == "robot-123").first()
    assert robot.connection_status == "OFFLINE"
    
    # Verify Redis cleanup
    assert "robot:heartbeat:robot-123" not in mock_redis.store
    assert "robot:control_lease:robot-123" not in mock_redis.store
    
    # Verify Kafka offline request published
    assert len(test_events) == 2
    assert any(t[0] == "rex.notification.robot.offline.requested.v1" for t in test_events)
    assert any(t[0] == "rex.robot.disconnected.v1" for t in test_events)
