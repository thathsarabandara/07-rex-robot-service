"""Tests for authentication endpoints"""

import pytest


def test_robot_login(client):
    """Test robot login and JWT token generation"""
    # Register a robot
    robot_response = client.post(
        "/api/robots/register",
        json={
            "name": "REX-001",
            "model": "REX-Pro-v2",
            "serial_number": "REX-SN-20240422-001",
            "firmware_version": "2.1.0",
        }
    )
    
    robot_id = robot_response.json()["robot_id"]
    
    # Attempt login
    response = client.post(
        "/api/auth/login",
        json={
            "robot_id": robot_id,
            "fingerprint": {
                "hardware_id": "hw-001",
                "mac_address": "00:1A:2B:3C:4D:5E",
                "cpu_info": "ARM Cortex-A72",
                "os_info": "Ubuntu 22.04 LTS",
                "system_uuid": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] > 0


def test_login_nonexistent_robot(client):
    """Test login with nonexistent robot"""
    response = client.post(
        "/api/auth/login",
        json={
            "robot_id": "NONEXISTENT",
            "fingerprint": {
                "hardware_id": "hw-001",
                "mac_address": "00:1A:2B:3C:4D:5E",
                "cpu_info": "ARM Cortex-A72",
                "os_info": "Ubuntu 22.04 LTS",
                "system_uuid": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    )
    
    assert response.status_code == 401
