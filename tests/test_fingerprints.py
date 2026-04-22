"""Tests for fingerprinting endpoints"""

import pytest


def test_register_fingerprint(client):
    """Test fingerprint registration"""
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
    
    # Register fingerprint
    response = client.post(
        f"/api/fingerprints/register/{robot_id}",
        json={
            "hardware_id": "hw-001",
            "mac_address": "00:1A:2B:3C:4D:5E",
            "cpu_info": "ARM Cortex-A72",
            "os_info": "Ubuntu 22.04 LTS",
            "system_uuid": "550e8400-e29b-41d4-a716-446655440000"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "fingerprint_hash" in data
    assert data["hardware_id"] == "hw-001"


def test_check_fingerprint_strength(client):
    """Test fingerprint strength check"""
    response = client.post(
        "/api/fingerprints/strength",
        json={
            "hardware_id": "hw-001",
            "mac_address": "00:1A:2B:3C:4D:5E",
            "cpu_info": "ARM Cortex-A72",
            "os_info": "Ubuntu 22.04 LTS",
            "system_uuid": "550e8400-e29b-41d4-a716-446655440000"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["strength"] in ["STRONG", "MEDIUM", "WEAK"]
