from app.models.robot import Robot
from app.models.robot_event import RobotEvent
from app.services.kafka_service import test_events
from app.services.mqtt_service import test_publications


def test_unpair_robot_success(client, generate_user_jwt, db):
    token = generate_user_jwt("user-123")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Register and claim
    reg_resp = client.post("/api/v1/robots/register", json={
        "serial_number": "REX-ESP32-0001",
        "hardware_model": "REX-47",
        "name": "REX-47"
    }, headers=headers).json()
    robot_id = reg_resp["robot_id"]
    secret = reg_resp["robot_secret"]
    
    client.post("/api/v1/robots/claim", json={"robot_id": robot_id, "robot_secret": secret}, headers=headers)
    
    test_events.clear()
    test_publications.clear()
    
    # 2. Unpair
    response = client.delete(f"/api/v1/robots/{robot_id}/claim", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["message"] == "Robot unpaired successfully"
    assert data["robot_id"] == robot_id
    assert data["status"] == "UNCLAIMED"
    
    # 3. Check DB
    robot = db.query(Robot).filter(Robot.id == robot_id).first()
    assert robot.owner_user_id is None
    assert robot.status == "UNCLAIMED"
    assert robot.current_mode == "IDLE"
    assert robot.secret_rotation_required is True
    
    # Verify that secret was rotated (the hash shouldn't match the original secret)
    from app.utils.secrets import verify_secret
    assert not verify_secret(robot.device_secret_hash, secret)
    
    # Verify events
    events = db.query(RobotEvent).filter(RobotEvent.robot_id == robot_id).all()
    assert any(e.event_type == "robot_unpaired" for e in events)
    
    # Verify MQTT Emergency Stop published
    assert len(test_publications) == 1
    assert test_publications[0][0] == f"rex/robots/{robot_id}/commands/emergency-stop"
    assert test_publications[0][1]["active"] is True
    assert test_publications[0][2] == 1 # QoS 1
    
    # Verify Kafka events
    assert len(test_events) == 2
    assert any(t[0] == "rex.notification.robot.unpaired.requested.v1" for t in test_events)
    assert any(t[0] == "rex.robot.unpaired.v1" for t in test_events)

def test_unpair_robot_unauthorized(client, generate_user_jwt, db):
    token1 = generate_user_jwt("user-123")
    headers1 = {"Authorization": f"Bearer {token1}"}
    token2 = generate_user_jwt("user-456")
    headers2 = {"Authorization": f"Bearer {token2}"}
    
    reg_resp = client.post("/api/v1/robots/register", json={
        "serial_number": "REX-ESP32-0001",
        "hardware_model": "REX-47",
        "name": "REX-47"
    }, headers=headers1).json()
    robot_id = reg_resp["robot_id"]
    secret = reg_resp["robot_secret"]
    
    # Claim by user 1
    client.post("/api/v1/robots/claim", json={"robot_id": robot_id, "robot_secret": secret}, headers=headers1)
    
    # Unpair attempt by user 2
    response = client.delete(f"/api/v1/robots/{robot_id}/claim", headers=headers2)
    assert response.status_code == 403
    assert "You do not own this robot" in response.json()["message"]
