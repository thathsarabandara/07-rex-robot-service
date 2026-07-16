def test_list_and_get_robots(client, generate_user_jwt):
    token1 = generate_user_jwt("user-123")
    headers1 = {"Authorization": f"Bearer {token1}"}
    token2 = generate_user_jwt("user-456")
    headers2 = {"Authorization": f"Bearer {token2}"}
    
    # User 1 registers robot
    reg_payload = {
        "serial_number": "REX-ESP32-0001",
        "hardware_model": "REX-47",
        "name": "REX-47"
    }
    reg_resp = client.post("/api/v1/robots/register", json=reg_payload, headers=headers1).json()
    robot_id = reg_resp["robot_id"]
    secret = reg_resp["robot_secret"]
    
    # Claim robot
    client.post("/api/v1/robots/claim", json={"robot_id": robot_id, "robot_secret": secret}, headers=headers1)
    
    # 1. User 1 lists robots -> should contain 1 robot
    list_resp1 = client.get("/api/v1/robots", headers=headers1)
    assert list_resp1.status_code == 200
    assert len(list_resp1.json()) == 1
    assert list_resp1.json()[0]["id"] == robot_id
    
    # 2. User 2 lists robots -> should contain 0 robots
    list_resp2 = client.get("/api/v1/robots", headers=headers2)
    assert list_resp2.status_code == 200
    assert len(list_resp2.json()) == 0
    
    # 3. User 1 gets details -> 200
    get_resp1 = client.get(f"/api/v1/robots/{robot_id}", headers=headers1)
    assert get_resp1.status_code == 200
    assert get_resp1.json()["name"] == "REX-47"
    
    # 4. User 2 gets details -> 403 Forbidden
    get_resp2 = client.get(f"/api/v1/robots/{robot_id}", headers=headers2)
    assert get_resp2.status_code == 403

def test_update_robot_profile(client, generate_user_jwt):
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
    
    # Update profile
    patch_payload = {
        "name": "REX Living Room",
        "description": "Main home assistant robot",
        "location_label": "Living Room"
    }
    
    response = client.patch(f"/api/v1/robots/{robot_id}", json=patch_payload, headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == "REX Living Room"
    assert data["description"] == "Main home assistant robot"
    assert data["location_label"] == "Living Room"
    
    # Ensure serial, owner or ID cannot be modified by patch (not allowed fields in schema)
    patch_payload_invalid = {
        "id": "new-uuid",
        "serial_number": "new-serial",
        "owner_user_id": "other-user-uuid",
        "status": "UNCLAIMED"
    }
    response2 = client.patch(f"/api/v1/robots/{robot_id}", json=patch_payload_invalid, headers=headers)
    assert response2.status_code == 200
    # Values should remain unchanged
    data2 = response2.json()
    assert data2["id"] == robot_id
    assert data2["serial_number"] == "REX-ESP32-0001"
    assert data2["owner_user_id"] == "user-123"
    assert data2["status"] == "CLAIMED"
patch_payload = {}
