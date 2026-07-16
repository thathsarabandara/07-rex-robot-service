from app.services.control_lease_service import (
    acquire_control_lease,
    get_control_lease_status,
    is_lease_owner,
    release_control_lease,
)


def test_control_lease_endpoints(client, generate_user_jwt):
    token1 = generate_user_jwt("user-123")
    headers1 = {"Authorization": f"Bearer {token1}"}
    generate_user_jwt("user-456")
    
    # 1. Setup robot
    reg_resp = client.post("/api/v1/robots/register", json={
        "serial_number": "REX-ESP32-0001",
        "hardware_model": "REX-47",
        "name": "REX-47"
    }, headers=headers1).json()
    robot_id = reg_resp["robot_id"]
    secret = reg_resp["robot_secret"]
    client.post("/api/v1/robots/claim", json={"robot_id": robot_id, "robot_secret": secret}, headers=headers1)
    
    # 2. Acquire Lease
    acquire_payload = {
        "control_channel": "WEB",
        "connection_id": "conn-1"
    }
    
    resp_acq1 = client.post(f"/api/v1/robots/{robot_id}/control/acquire", json=acquire_payload, headers=headers1)
    assert resp_acq1.status_code == 200
    assert resp_acq1.json()["acquired"] is True
    assert resp_acq1.json()["connection_id"] == "conn-1"
    
    # Check status endpoint
    status_resp1 = client.get(f"/api/v1/robots/{robot_id}/control/status", headers=headers1)
    assert status_resp1.status_code == 200
    assert status_resp1.json()["leased"] is True
    assert status_resp1.json()["lease"]["connection_id"] == "conn-1"
    
    # 3. Collision: Try to acquire from different connection ID
    acquire_payload_conflict = {
        "control_channel": "MOBILE",
        "connection_id": "conn-2"
    }
    resp_acq2 = client.post(f"/api/v1/robots/{robot_id}/control/acquire", json=acquire_payload_conflict, headers=headers1)
    assert resp_acq2.status_code == 409
    assert "already held" in resp_acq2.json()["message"]
    
    # 4. Release Lease
    resp_rel = client.delete(f"/api/v1/robots/{robot_id}/control/release?connection_id=conn-1", headers=headers1)
    assert resp_rel.status_code == 200
    
    # Check status again -> should be unleased
    status_resp2 = client.get(f"/api/v1/robots/{robot_id}/control/status", headers=headers1)
    assert status_resp2.status_code == 200
    assert status_resp2.json()["leased"] is False

async def test_control_lease_service_methods(mock_redis):
    # Test service methods directly
    # Clear redis mock store
    mock_redis.store.clear()
    
    # Acquire
    success = await acquire_control_lease("robot-123", "user-123", "conn-abc", "WEB", 10)
    assert success is True
    
    # Check lease owner
    assert await is_lease_owner("robot-123", "user-123", "conn-abc") is True
    assert await is_lease_owner("robot-123", "user-123", "conn-wrong") is False
    
    # Release
    rel = await release_control_lease("robot-123", "user-123", "conn-abc")
    assert rel is True
    
    status_info = await get_control_lease_status("robot-123")
    assert status_info is None
