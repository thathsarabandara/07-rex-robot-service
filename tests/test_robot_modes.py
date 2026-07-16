from app.models.robot import Robot
from app.models.robot_command import RobotCommand
from app.services.kafka_service import test_events
from app.services.mqtt_service import test_publications


def test_change_mode_success(client, generate_user_jwt, db):
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
    
    robot = db.query(Robot).filter(Robot.id == robot_id).first()
    robot.connection_status = "ONLINE"
    db.commit()
    
    test_events.clear()
    test_publications.clear()
    
    # Change mode
    response = client.post(f"/api/v1/robots/{robot_id}/mode", json={"mode": "LINE_FOLLOWING"}, headers=headers)
    assert response.status_code == 202
    
    data = response.json()
    assert data["message"] == "Mode change command issued"
    assert data["mode"] == "LINE_FOLLOWING"
    assert "command_id" in data
    
    # Verify DB Command
    cmd = db.query(RobotCommand).filter(RobotCommand.id == data["command_id"]).first()
    assert cmd is not None
    assert cmd.command_type == "MODE_CHANGE"
    assert cmd.payload["mode"] == "LINE_FOLLOWING"
    assert cmd.status == "PENDING"
    
    # Verify MQTT command
    assert len(test_publications) == 1
    assert test_publications[0][0] == f"rex/robots/{robot_id}/commands/mode"
    assert test_publications[0][1]["mode"] == "LINE_FOLLOWING"
    assert test_publications[0][1]["command_id"] == cmd.id
    
    # Verify Kafka Event
    assert len(test_events) == 1
    assert test_events[0][0] == "rex.robot.mode-changed.v1"

def test_change_mode_failures(client, generate_user_jwt, db):
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
    
    # 1. Robot is OFFLINE -> Reject mode change
    response1 = client.post(f"/api/v1/robots/{robot_id}/mode", json={"mode": "LINE_FOLLOWING"}, headers=headers)
    assert response1.status_code == 400
    assert "Robot is offline" in response1.json()["message"]
    
    # Set ONLINE but active E-STOP
    robot = db.query(Robot).filter(Robot.id == robot_id).first()
    robot.connection_status = "ONLINE"
    robot.emergency_stop_active = True
    db.commit()
    
    # 2. E-Stop Active -> Reject mode change
    response2 = client.post(f"/api/v1/robots/{robot_id}/mode", json={"mode": "LINE_FOLLOWING"}, headers=headers)
    assert response2.status_code == 400
    assert "Emergency Stop is active" in response2.json()["message"]
