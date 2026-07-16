from app.models.robot import Robot
from app.models.robot_configuration import RobotConfiguration
from app.models.robot_event import RobotEvent
from app.services.kafka_service import test_events
from app.utils.secrets import verify_secret


def test_register_robot_success(client, generate_user_jwt, db):
    token = generate_user_jwt("user-123")
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "serial_number": "REX-ESP32-0001",
        "hardware_model": "REX-47",
        "name": "REX-47"
    }
    
    response = client.post("/api/v1/robots/register", json=payload, headers=headers)
    assert response.status_code == 201
    
    data = response.json()
    assert data["serial_number"] == "REX-ESP32-0001"
    assert data["status"] == "UNCLAIMED"
    assert "robot_id" in data
    assert "robot_secret" in data
    
    # Verify in DB
    robot = db.query(Robot).filter(Robot.id == data["robot_id"]).first()
    assert robot is not None
    assert robot.serial_number == "REX-ESP32-0001"
    assert robot.owner_user_id is None
    assert verify_secret(robot.device_secret_hash, data["robot_secret"])
    
    # Verify Configuration exists
    config = db.query(RobotConfiguration).filter(RobotConfiguration.robot_id == robot.id).first()
    assert config is not None
    assert config.base_max_speed == 100
    
    # Verify events
    events = db.query(RobotEvent).filter(RobotEvent.robot_id == robot.id).all()
    assert len(events) == 1
    assert events[0].event_type == "robot_registered"
    
    # Verify Kafka event published
    assert len(test_events) == 1
    assert test_events[0][0] == "rex.robot.registered.v1"
    assert test_events[0][1]["event_type"] == "robot_registered"

def test_register_robot_invalid_serial(client, generate_user_jwt):
    token = generate_user_jwt("user-123")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Missing REX prefix and format
    payload = {
        "serial_number": "ESP32-0001",
        "hardware_model": "REX-47",
        "name": "REX-47"
    }
    
    response = client.post("/api/v1/robots/register", json=payload, headers=headers)
    assert response.status_code == 400
    assert "Invalid serial number" in response.json()["message"]

def test_register_robot_duplicate_serial(client, generate_user_jwt, db):
    token = generate_user_jwt("user-123")
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "serial_number": "REX-ESP32-0001",
        "hardware_model": "REX-47",
        "name": "REX-47"
    }
    
    # First call
    response1 = client.post("/api/v1/robots/register", json=payload, headers=headers)
    assert response1.status_code == 201
    
    # Second call
    response2 = client.post("/api/v1/robots/register", json=payload, headers=headers)
    assert response2.status_code == 400
    assert "already registered" in response2.json()["message"]
