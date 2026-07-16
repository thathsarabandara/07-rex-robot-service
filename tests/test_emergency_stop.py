from app.models.robot import Robot
from app.models.robot_command import RobotCommand
from app.models.robot_event import RobotEvent
from app.services.kafka_service import test_events
from app.services.mqtt_service import test_publications


def test_trigger_emergency_stop(client, generate_user_jwt, db, mock_redis):
    token = generate_user_jwt("user-123")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Setup robot
    reg_resp = client.post("/api/v1/robots/register", json={
        "serial_number": "REX-ESP32-0001",
        "hardware_model": "REX-47",
        "name": "REX-47"
    }, headers=headers).json()
    robot_id = reg_resp["robot_id"]
    secret = reg_resp["robot_secret"]
    client.post("/api/v1/robots/claim", json={"robot_id": robot_id, "robot_secret": secret}, headers=headers)
    
    # Set online and insert a pending command
    robot = db.query(Robot).filter(Robot.id == robot_id).first()
    robot.connection_status = "ONLINE"
    
    pending_cmd = RobotCommand(
        robot_id=robot_id,
        issued_by_user_id="user-123",
        command_type="MOVE",
        status="PENDING"
    )
    db.add(pending_cmd)
    
    # Put control lease in Redis
    mock_redis.store[f"robot:control_lease:{robot_id}"] = {"connection_id": "conn-1"}
    db.commit()
    
    test_events.clear()
    test_publications.clear()
    
    # Trigger stop
    response = client.post(f"/api/v1/robots/{robot_id}/emergency-stop", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["message"] == "Emergency Stop activated successfully"
    assert "command_id" in data
    
    # Verify DB state
    db.refresh(robot)
    assert robot.emergency_stop_active is True
    assert robot.current_mode == "EMERGENCY_STOP"
    
    # Verify lease deleted
    assert f"robot:control_lease:{robot_id}" not in mock_redis.store
    
    # Verify pending commands failed
    db.refresh(pending_cmd)
    assert pending_cmd.status == "FAILED"
    assert pending_cmd.failure_reason == "EMERGENCY_STOP_TRIGGERED"
    
    # Verify events
    events = db.query(RobotEvent).filter(RobotEvent.robot_id == robot_id).all()
    assert any(e.event_type == "emergency_stop" and e.severity == "CRITICAL" for e in events)
    
    # Verify MQTT command
    assert len(test_publications) == 1
    assert test_publications[0][0] == f"rex/robots/{robot_id}/commands/emergency-stop"
    assert test_publications[0][1]["active"] is True
    assert test_publications[0][2] == 1  # QoS 1
    
    # Verify Kafka events
    assert len(test_events) == 2
    assert any(t[0] == "rex.notification.robot.emergency-stop.requested.v1" for t in test_events)
    assert any(t[0] == "rex.robot.emergency-stop-activated.v1" for t in test_events)

def test_release_emergency_stop(client, generate_user_jwt, db):
    token = generate_user_jwt("user-123")
    headers = {"Authorization": f"Bearer {token}"}
    
    reg_resp = client.post("/api/v1/robots/register", json={
        "serial_number": "REX-ESP32-0001",
        "hardware_model": "REX-47",
        "name": "REX-47"
    }, headers=headers).json()
    robot_id = reg_resp["robot_id"]
    secret = reg_resp["robot_secret"]
    client.post("/api/v1/robots/claim", json={"robot_id": robot_id, "robot_secret": secret}, headers=headers)
    
    robot = db.query(Robot).filter(Robot.id == robot_id).first()
    robot.connection_status = "ONLINE"
    robot.emergency_stop_active = True
    robot.current_mode = "EMERGENCY_STOP"
    db.commit()
    
    test_events.clear()
    test_publications.clear()
    
    # Release E-Stop
    response = client.post(f"/api/v1/robots/{robot_id}/emergency-stop/release", headers=headers)
    assert response.status_code == 202
    
    data = response.json()
    assert data["message"] == "Emergency Stop release command issued"
    
    # Verify MQTT publication
    assert len(test_publications) == 1
    assert test_publications[0][0] == f"rex/robots/{robot_id}/commands/emergency-stop"
    assert test_publications[0][1]["active"] is False
    assert test_publications[0][2] == 1  # QoS 1
    
    # Verify Kafka Event
    assert len(test_events) == 1
    assert test_events[0][0] == "rex.robot.emergency-stop-released.v1"
