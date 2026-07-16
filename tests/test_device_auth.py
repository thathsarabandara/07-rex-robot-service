from app.models.device_session import RobotDeviceSession
from app.services.kafka_service import test_events


def test_device_authenticate_success(client, generate_user_jwt, db):
    # 1. Provision a robot
    user_token = generate_user_jwt("user-123")
    headers = {"Authorization": f"Bearer {user_token}"}
    reg_resp = client.post("/api/v1/robots/register", json={
        "serial_number": "REX-ESP32-0001",
        "hardware_model": "REX-47",
        "name": "REX-47"
    }, headers=headers).json()
    robot_id = reg_resp["robot_id"]
    secret = reg_resp["robot_secret"]
    
    test_events.clear()
    
    # 2. Authenticate device
    auth_payload = {
        "robot_id": robot_id,
        "robot_secret": secret,
        "firmware_version": "1.2.3"
    }
    
    response = client.post("/api/v1/device/authenticate", json=auth_payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"
    assert data["mqtt"]["client_id"] == f"rex-robot-{robot_id}"
    
    # Check DB session
    session = db.query(RobotDeviceSession).filter(RobotDeviceSession.robot_id == robot_id).first()
    assert session is not None
    assert session.firmware_version == "1.2.3"
    
    # Verify Kafka trigger
    assert len(test_events) == 1
    assert test_events[0][0] == "rex.robot.authenticated.v1"

def test_device_authenticate_invalid(client, generate_user_jwt):
    user_token = generate_user_jwt("user-123")
    headers = {"Authorization": f"Bearer {user_token}"}
    reg_resp = client.post("/api/v1/robots/register", json={
        "serial_number": "REX-ESP32-0001",
        "hardware_model": "REX-47",
        "name": "REX-47"
    }, headers=headers).json()
    robot_id = reg_resp["robot_id"]
    
    auth_payload = {
        "robot_id": robot_id,
        "robot_secret": "wrong-secret"
    }
    response = client.post("/api/v1/device/authenticate", json=auth_payload)
    assert response.status_code == 401
    assert "Invalid robot credentials" in response.json()["message"]

def test_device_token_refresh(client, generate_user_jwt, db):
    user_token = generate_user_jwt("user-123")
    headers = {"Authorization": f"Bearer {user_token}"}
    reg_resp = client.post("/api/v1/robots/register", json={
        "serial_number": "REX-ESP32-0001",
        "hardware_model": "REX-47",
        "name": "REX-47"
    }, headers=headers).json()
    robot_id = reg_resp["robot_id"]
    secret = reg_resp["robot_secret"]
    
    auth_data = client.post("/api/v1/device/authenticate", json={
        "robot_id": robot_id,
        "robot_secret": secret,
        "firmware_version": "1.0.0"
    }).json()
    
    refresh_token = auth_data["refresh_token"]
    
    # Refresh
    refresh_resp = client.post("/api/v1/device/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 200
    
    data = refresh_resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    
    # Check old session revoked
    from app.services.device_auth_service import hash_token
    old_session = db.query(RobotDeviceSession).filter(
        RobotDeviceSession.refresh_token_hash == hash_token(refresh_token)
    ).first()
    assert old_session.revoked_at is not None

def test_device_logout_and_get_config(client, generate_user_jwt, db):
    user_token = generate_user_jwt("user-123")
    headers = {"Authorization": f"Bearer {user_token}"}
    reg_resp = client.post("/api/v1/robots/register", json={
        "serial_number": "REX-ESP32-0001",
        "hardware_model": "REX-47",
        "name": "REX-47"
    }, headers=headers).json()
    robot_id = reg_resp["robot_id"]
    secret = reg_resp["robot_secret"]
    
    auth_data = client.post("/api/v1/device/authenticate", json={
        "robot_id": robot_id,
        "robot_secret": secret
    }).json()
    
    access_token = auth_data["access_token"]
    device_headers = {"Authorization": f"Bearer {access_token}"}
    
    # 1. Fetch config with device credentials
    config_resp = client.get("/api/v1/device/config", headers=device_headers)
    assert config_resp.status_code == 200
    assert config_resp.json()["base_max_speed"] == 100
    
    # 2. Invalidate sessions (Logout)
    logout_resp = client.post("/api/v1/device/logout", headers=device_headers)
    assert logout_resp.status_code == 204
    
    # 3. Retrieve config again with old access token -> should fail
    config_resp2 = client.get("/api/v1/device/config", headers=device_headers)
    assert config_resp2.status_code == 401
