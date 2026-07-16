import asyncio
import json

import pytest

from app.models.robot import Robot
from app.models.robot_command import RobotCommand
from app.services.kafka_service import test_events
from app.workers.mqtt_consumer import handle_mqtt_message


@pytest.mark.asyncio
async def test_handle_command_acknowledgement_success(db):
    # Setup robot and command
    db_robot = Robot(
        id="robot-123",
        serial_number="REX-ESP32-9999",
        hardware_model="REX-47",
        name="REX-47",
        device_secret_hash="hash",
        status="CLAIMED"
    )
    db_command = RobotCommand(
        id="cmd-abc",
        robot_id="robot-123",
        command_type="MODE_CHANGE",
        status="PENDING"
    )
    db.add(db_robot)
    db.add(db_command)
    db.commit()
    
    test_events.clear()
    
    # Simulate receiving COMPLETED ack payload from MQTT
    ack_payload = {
        "command_id": "cmd-abc",
        "robot_id": "robot-123",
        "status": "COMPLETED",
        "message": "Mode change success",
        "timestamp": "2026-07-15T12:00:00Z"
    }
    
    await handle_mqtt_message("rex/robots/robot-123/acknowledgements", json.dumps(ack_payload))
    
    # Check DB command status -> should be COMPLETED
    db.expire_all()
    cmd = db.query(RobotCommand).filter(RobotCommand.id == "cmd-abc").first()
    assert cmd.status == "COMPLETED"
    assert cmd.completed_at is not None
    assert len(test_events) == 0 # No failure notifications

@pytest.mark.asyncio
async def test_handle_command_acknowledgement_failure(db):
    # Setup robot and command
    db_robot = Robot(
        id="robot-123",
        serial_number="REX-ESP32-9999",
        hardware_model="REX-47",
        name="REX-47",
        device_secret_hash="hash",
        status="CLAIMED"
    )
    db_command = RobotCommand(
        id="cmd-abc",
        robot_id="robot-123",
        command_type="MODE_CHANGE",
        status="PENDING"
    )
    db.add(db_robot)
    db.add(db_command)
    db.commit()
    
    test_events.clear()
    
    # Simulate receiving FAILED ack payload from MQTT
    ack_payload = {
        "command_id": "cmd-abc",
        "robot_id": "robot-123",
        "status": "FAILED",
        "message": "Mode transition rejected due to motor block",
        "timestamp": "2026-07-15T12:00:00Z"
    }
    
    await handle_mqtt_message("rex/robots/robot-123/acknowledgements", json.dumps(ack_payload))
    await asyncio.sleep(0.1)
    
    # Check DB command status -> should be FAILED
    db.expire_all()
    cmd = db.query(RobotCommand).filter(RobotCommand.id == "cmd-abc").first()
    assert cmd.status == "FAILED"
    assert cmd.failure_reason == "Mode transition rejected due to motor block"
    assert cmd.completed_at is not None
    
    # Verify Kafka failure triggers
    assert len(test_events) == 2
    assert any(t[0] == "rex.notification.robot.command-failed.requested.v1" for t in test_events)
    assert any(t[0] == "rex.robot.command-failed.v1" for t in test_events)
