from app.models.robot import Robot
from app.services.mqtt_service import test_publications


def test_arm_websocket_commands(client, generate_user_jwt, db):
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
    
    test_publications.clear()
    
    with client.websocket_connect(f"/api/v1/ws/robots/{robot_id}/arm?token={token}") as websocket:
        # 1. ARM_JOINT single joint angle test
        joint_msg = {
            "type": "ARM_JOINT",
            "joint": "SHOULDER",
            "angle": 120,
            "speed": 35,
            "sequence": 501
        }
        websocket.send_json(joint_msg)
        
        import time
        time.sleep(0.1)
        
        assert len(test_publications) == 1
        assert test_publications[0][0] == f"rex/robots/{robot_id}/commands/arm"
        assert test_publications[0][1]["type"] == "ARM_JOINT"
        assert test_publications[0][1]["joint"] == "SHOULDER"
        assert test_publications[0][1]["angle"] == 120
        assert test_publications[0][1]["speed"] == 35
        
        # 2. ARM_POSE multi-joint angle pose test
        pose_msg = {
            "type": "ARM_POSE",
            "joints": {
                "base": 90,
                "shoulder": 80,
                "elbow": 110,
                "grip": 50
            },
            "speed": 30,
            "sequence": 502
        }
        websocket.send_json(pose_msg)
        time.sleep(0.1)
        
        assert len(test_publications) == 2
        assert test_publications[1][1]["type"] == "ARM_POSE"
        assert test_publications[1][1]["joints"]["base"] == 90
        assert test_publications[1][1]["joints"]["shoulder"] == 80
        assert test_publications[1][1]["joints"]["elbow"] == 110
        assert test_publications[1][1]["joints"]["grip"] == 50
        assert test_publications[1][1]["speed"] == 30
        
        # 3. ARM_STOP command test
        stop_msg = {
            "type": "ARM_STOP"
        }
        websocket.send_json(stop_msg)
        time.sleep(0.1)
        
        assert len(test_publications) == 3
        assert test_publications[2][1]["type"] == "ARM_STOP"
