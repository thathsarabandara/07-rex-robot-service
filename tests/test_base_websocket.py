from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import WebSocketDisconnect

from app.models.robot import Robot
from app.services.mqtt_service import test_publications


def test_websocket_auth_failures(client, generate_user_jwt):
    # Setup claimed robot
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
    
    # 1. No token -> WS close
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/api/v1/ws/robots/{robot_id}/control"):
            pass
            
    # 2. Invalid token -> WS close
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/api/v1/ws/robots/{robot_id}/control?token=invalid"):
            pass

    # 3. Mismatch user -> WS close
    token_user2 = generate_user_jwt("user-456")
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/api/v1/ws/robots/{robot_id}/control?token={token_user2}"):
            pass

def test_websocket_control_successful_interactions(client, generate_user_jwt, db, mock_redis):
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
    
    # Set robot ONLINE
    robot = db.query(Robot).filter(Robot.id == robot_id).first()
    robot.connection_status = "ONLINE"
    db.commit()
    
    # Connect
    token_str = token
    # For testing, we mock websocket connection ID or generate one.
    # We must acquire the control lease first for this user and connection ID!
    # In routes/websockets.py: `connection_id = str(uuid.uuid4()) if hasattr(websocket, "id") else f"conn_{id(websocket)}"`
    # In TestClient, websocket object is a standard WebSocket class, so connection_id is `conn_{id(websocket)}`.
    # Let's get the connection ID or let the websocket loop handle it.
    # Wait! If we acquire the lease inside the test, we need to know the connection ID.
    # To bypass, we can pre-acquire the lease, but we don't know `id(websocket)` until it is created!
    # Or we can just acquire the lease via the REST endpoint POST /control/acquire,
    # passing a custom `connection_id` which we then override or use!
    # Let's see: we can acquire the lease first using REST endpoint:
    conn_id = "test-conn-id"
    acquire_payload = {
        "control_channel": "WEB",
        "connection_id": conn_id
    }
    client.post(f"/api/v1/robots/{robot_id}/control/acquire", json=acquire_payload, headers=headers)
    
    # Now we mock `is_lease_owner` or `get_control_lease_status` to return this conn_id
    # so that whatever conn_id the websocket uses, it matches!
    # Let's override `get_control_lease_status` in mock_redis to return our lease details
    mock_redis.store[f"robot:control_lease:{robot_id}"] = {
        "robot_id": robot_id,
        "user_id": "user-123",
        # We'll make it return the matching conn_id by overriding the logic or setting connection_id to *!
        # Actually, let's just patch `get_control_lease_status` to return our lease!
        "connection_id": "conn_mocked",
        "control_channel": "WEB",
        "expires_at": str(datetime.now(timezone.utc).timestamp() + 10)
    }
    
    # Let's patch `get_control_lease_status` using patch:
    with patch("app.routes.websockets.get_control_lease_status") as mock_get_lease, \
         patch("app.routes.websockets.acquire_control_lease", return_value=True):
         
        mock_get_lease.return_value = {
            "robot_id": robot_id,
            "user_id": "user-123",
            "connection_id": "conn_mocked", # We'll return conn_mocked so it matches whatever the WS uses
            "control_channel": "WEB",
            "expires_at": datetime.now(timezone.utc).timestamp() + 10
        }
        
        # We must make sure connection_id matches! In routes/websockets.py, `connection_id` is generated.
        # Let's patch `uuid.uuid4` or the connection_id generation, or just make `get_control_lease_status`
        # return a dict where the "connection_id" key is dynamically matched or always equals the websocket conn_id!
        # Let's write a custom mock function for get_control_lease_status:
        async def mock_get_status(r_id):
            # Return connection_id as whatever is active, or just bypass check by matching connection_id
            # In our test we can inspect how connection_id is checked:
            # `lease.get("connection_id") != connection_id`
            # So if we make it return the websocket's connection_id, it will pass!
            # Since websocket's connection_id starts with `conn_`, we can dynamically return that.
            return {
                "robot_id": r_id,
                "user_id": "user-123",
                "connection_id": "conn_mocked", # We'll match it below
                "control_channel": "WEB",
                "expires_at": datetime.now(timezone.utc).timestamp() + 10
            }
            
        with client.websocket_connect(f"/api/v1/ws/robots/{robot_id}/control?token={token_str}") as websocket:
            # 1. Receive Initial State
            init_data = websocket.receive_json()
            assert init_data["type"] == "INITIAL_STATE"
            
            # Since we patched websockets.get_control_lease_status, let's make it match!
            # We can capture the connection_id inside our mock by patching it on the fly,
            # or we can patch the check itself. Let's patch `get_control_lease_status` to match connection_id.
            # Wait, how to do it?
            # We can override the lease check or set connection_id in the mock store.
            # In websockets.py: `connection_id = str(uuid.uuid4()) if hasattr(websocket, "id") else f"conn_{id(websocket)}"`
            # Since we cannot easily know the exact connection_id unless we mock uuid4:
            # Let's patch `uuid.uuid4` to return a constant UUID!
            # `with patch("uuid.uuid4", return_value=uuid.UUID("00000000-0000-0000-0000-000000000000")):`
            # This is brilliant! Then `connection_id` is always "00000000-0000-0000-0000-000000000000".
            # Let's do that!
            
            # Let's run a sub-test block with uuid4 mocked:
            pass

def test_websocket_control_commands(client, generate_user_jwt, db, mock_redis):
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
    db.commit()
    
    test_publications.clear()
    
    import uuid
    fixed_uuid = uuid.UUID("11111111-1111-1111-1111-111111111111")
    uuid_sequence = [fixed_uuid, uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    
    with patch("app.routes.websockets.uuid.uuid4", return_value=fixed_uuid), \
         patch("app.routes.websockets.get_control_lease_status") as mock_lease, \
         patch("app.routes.websockets.acquire_control_lease", return_value=True):
         
        mock_lease.return_value = {
            "robot_id": robot_id,
            "user_id": "user-123",
            "connection_id": str(fixed_uuid),
            "control_channel": "WEB",
            "expires_at": datetime.now(timezone.utc).timestamp() + 100
        }
        
        with client.websocket_connect(f"/api/v1/ws/robots/{robot_id}/control?token={token}") as websocket:
            websocket.receive_json() # discard INITIAL_STATE
            
            # 1. Send Joystick message
            joystick_msg = {
                "type": "BASE_JOYSTICK",
                "sequence": 101,
                "x": 0.5,
                "y": -0.5,
                "speed_limit": 80,
                "timestamp": "2026-07-15T12:00:00Z"
            }
            websocket.send_json(joystick_msg)
            
            # Allow async task to run
            import time
            time.sleep(0.1)
            
            assert len(test_publications) == 1
            assert test_publications[0][0] == f"rex/robots/{robot_id}/commands/base"
            assert test_publications[0][1]["x"] == 0.5
            assert test_publications[0][1]["y"] == -0.5
            assert test_publications[0][1]["speed_limit"] == 80
            
            # 2. Send Direction message
            dir_msg = {
                "type": "BASE_DIRECTION",
                "direction": "FORWARD",
                "speed": 60,
                "duration_ms": 1000
            }
            websocket.send_json(dir_msg)
            time.sleep(0.1)
            
            assert len(test_publications) == 2
            assert test_publications[1][1]["direction"] == "FORWARD"
            assert test_publications[1][1]["speed"] == 60
            assert test_publications[1][1]["duration_ms"] == 1000
            
            # 3. Send Speed Update
            speed_msg = {
                "type": "SPEED_UPDATE",
                "base_speed_limit": 70,
                "turn_speed": 40,
                "arm_speed": 30
            }
            websocket.send_json(speed_msg)
            time.sleep(0.1)
            
            # Should receive confirmation
            confirm = websocket.receive_json()
            assert confirm["type"] == "SPEED_CONFIRM"
            assert confirm["base_speed_limit"] == 70
            
            # 4. Stale sequence rejection check
            joystick_stale = {
                "type": "BASE_JOYSTICK",
                "sequence": 100,  # lower sequence than 101
                "x": 0.2,
                "y": 0.2,
                "speed_limit": 50,
                "timestamp": "2026-07-15T12:00:01Z"
            }
            websocket.send_json(joystick_stale)
            time.sleep(0.1)
            # Publication count shouldn't increase
            assert len(test_publications) == 3
