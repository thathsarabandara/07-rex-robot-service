from app.services.kafka_service import test_events
from app.services.mqtt_service import test_publications


def test_get_and_update_configuration(client, generate_user_jwt):
    token = generate_user_jwt("user-123")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Setup robot
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
    
    # 2. Get Config
    get_resp = client.get(f"/api/v1/robots/{robot_id}/config", headers=headers)
    assert get_resp.status_code == 200
    config_data = get_resp.json()
    assert config_data["version"] == 1
    assert config_data["base_max_speed"] == 100
    
    # 3. Update config
    update_payload = {
        "base_max_speed": 80,
        "base_default_speed": 50,
        "turn_speed": 45,
        "acceleration_step": 5,
        "braking_step": 10,
        "joystick_dead_zone": 0.08,
        "joystick_timeout_ms": 500,
        "obstacle_stop_distance_cm": 20,
        "arm_base_min_angle": 0,
        "arm_base_max_angle": 180,
        "arm_shoulder_min_angle": 20,
        "arm_shoulder_max_angle": 160,
        "arm_elbow_min_angle": 10,
        "arm_elbow_max_angle": 170,
        "arm_grip_min_angle": 20,
        "arm_grip_max_angle": 100,
        "arm_default_speed": 40,
        "heartbeat_interval_seconds": 5,
        "heartbeat_timeout_seconds": 20,
        "telemetry_interval_ms": 1000,
        "buzzer_enabled": True,
        "oled_eyes_enabled": True,
        "automatic_night_light": True
    }
    
    put_resp = client.put(f"/api/v1/robots/{robot_id}/config", json=update_payload, headers=headers)
    assert put_resp.status_code == 200
    updated_data = put_resp.json()
    assert updated_data["version"] == 2
    assert updated_data["base_max_speed"] == 80
    assert updated_data["arm_shoulder_min_angle"] == 20
    
    # 4. Verify triggers
    # MQTT config topic publish
    assert len(test_publications) == 1
    assert test_publications[0][0] == f"rex/robots/{robot_id}/commands/config"
    assert test_publications[0][1]["version"] == 2
    
    # Kafka config updated internal event
    assert len(test_events) == 1
    assert test_events[0][0] == "rex.robot.config-updated.v1"

def test_update_config_invalid_ranges(client, generate_user_jwt):
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
    
    # Invalid: default speed > max speed
    invalid_payload1 = {
        "base_max_speed": 50,
        "base_default_speed": 60,  # exceeds max
        "turn_speed": 45,
        "acceleration_step": 5,
        "braking_step": 10,
        "joystick_dead_zone": 0.08,
        "joystick_timeout_ms": 500,
        "obstacle_stop_distance_cm": 20,
        "arm_base_min_angle": 0,
        "arm_base_max_angle": 180,
        "arm_shoulder_min_angle": 20,
        "arm_shoulder_max_angle": 160,
        "arm_elbow_min_angle": 10,
        "arm_elbow_max_angle": 170,
        "arm_grip_min_angle": 20,
        "arm_grip_max_angle": 100,
        "arm_default_speed": 40,
        "heartbeat_interval_seconds": 5,
        "heartbeat_timeout_seconds": 20,
        "telemetry_interval_ms": 1000,
        "buzzer_enabled": True,
        "oled_eyes_enabled": True,
        "automatic_night_light": True
    }
    
    resp1 = client.put(f"/api/v1/robots/{robot_id}/config", json=invalid_payload1, headers=headers)
    assert resp1.status_code == 400
    assert "base_default_speed cannot exceed base_max_speed" in resp1.json()["message"]

    # Invalid: arm min angle > max angle
    invalid_payload2 = {
        "base_max_speed": 80,
        "base_default_speed": 50,
        "turn_speed": 45,
        "acceleration_step": 5,
        "braking_step": 10,
        "joystick_dead_zone": 0.08,
        "joystick_timeout_ms": 500,
        "obstacle_stop_distance_cm": 20,
        "arm_base_min_angle": 90,
        "arm_base_max_angle": 45,  # min exceeds max
        "arm_shoulder_min_angle": 20,
        "arm_shoulder_max_angle": 160,
        "arm_elbow_min_angle": 10,
        "arm_elbow_max_angle": 170,
        "arm_grip_min_angle": 20,
        "arm_grip_max_angle": 100,
        "arm_default_speed": 40,
        "heartbeat_interval_seconds": 5,
        "heartbeat_timeout_seconds": 20,
        "telemetry_interval_ms": 1000,
        "buzzer_enabled": True,
        "oled_eyes_enabled": True,
        "automatic_night_light": True
    }
    
    resp2 = client.put(f"/api/v1/robots/{robot_id}/config", json=invalid_payload2, headers=headers)
    assert resp2.status_code == 400
    assert "arm_base_min_angle cannot exceed arm_base_max_angle" in resp2.json()["message"]
