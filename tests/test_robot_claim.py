from app.models.robot import Robot
from app.models.robot_event import RobotEvent
from app.services.kafka_service import test_events


def test_claim_robot_success(client, generate_user_jwt, db):
    token = generate_user_jwt("user-123")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Register robot first
    reg_payload = {
        "serial_number": "REX-ESP32-0001",
        "hardware_model": "REX-47",
        "name": "REX-47"
    }
    reg_resp = client.post("/api/v1/robots/register", json=reg_payload, headers=headers).json()
    robot_id = reg_resp["robot_id"]
    secret = reg_resp["robot_secret"]
    
    # Reset test events log
    test_events.clear()
    
    # 2. Claim robot
    claim_payload = {
        "robot_id": robot_id,
        "robot_secret": secret
    }
    
    response = client.post("/api/v1/robots/claim", json=claim_payload, headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["message"] == "Robot claimed successfully"
    assert data["robot"]["id"] == robot_id
    assert data["robot"]["owner_user_id"] == "user-123"
    assert data["robot"]["status"] == "CLAIMED"
    
    # Verify DB state
    robot = db.query(Robot).filter(Robot.id == robot_id).first()
    assert robot.owner_user_id == "user-123"
    assert robot.status == "CLAIMED"
    assert robot.claimed_at is not None
    
    # Verify events log
    events = db.query(RobotEvent).filter(RobotEvent.robot_id == robot_id).all()
    # Should have registered and claimed events
    assert len(events) == 2
    assert any(e.event_type == "robot_claimed" for e in events)
    
    # Verify Kafka notification dispatch
    assert len(test_events) == 2
    assert any(t[0] == "rex.notification.robot.claimed.requested.v1" for t in test_events)
    assert any(t[0] == "rex.robot.claimed.v1" for t in test_events)

def test_claim_robot_invalid_secret(client, generate_user_jwt, db):
    token = generate_user_jwt("user-123")
    headers = {"Authorization": f"Bearer {token}"}
    
    reg_payload = {
        "serial_number": "REX-ESP32-0001",
        "hardware_model": "REX-47",
        "name": "REX-47"
    }
    reg_resp = client.post("/api/v1/robots/register", json=reg_payload, headers=headers).json()
    robot_id = reg_resp["robot_id"]
    
    # Incorrect secret
    claim_payload = {
        "robot_id": robot_id,
        "robot_secret": "wrong_secret"
    }
    
    response = client.post("/api/v1/robots/claim", json=claim_payload, headers=headers)
    assert response.status_code == 400
    assert response.json()["message"] == "Unable to claim robot"

def test_claim_robot_already_claimed(client, generate_user_jwt, db):
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
    
    # User 1 claims
    resp1 = client.post("/api/v1/robots/claim", json={"robot_id": robot_id, "robot_secret": secret}, headers=headers1)
    assert resp1.status_code == 200
    
    # User 2 claims
    resp2 = client.post("/api/v1/robots/claim", json={"robot_id": robot_id, "robot_secret": secret}, headers=headers2)
    assert resp2.status_code == 400
    assert resp2.json()["message"] == "Unable to claim robot"
