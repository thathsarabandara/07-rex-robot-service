"""Tests for device management endpoints"""

import pytest


def test_register_device(client):
    """Test device registration"""
    # Register a robot first
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
    
    # Register a device
    response = client.post(
        f"/api/devices/{robot_id}/register",
        json={
            "device_type": "ROBOT_PRIMARY",
            "name": "REX-PRIMARY-ETH0",
            "mac_address": "00:1A:2B:3C:4D:5E",
            "public_key": "-----BEGIN PUBLIC KEY-----\nMFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBALj...\n-----END PUBLIC KEY-----"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["device_id"].startswith("DEV-")
    assert data["mac_address"] == "00:1A:2B:3C:4D:5E"


def test_get_robot_devices(client):
    """Test getting devices for a robot"""
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
    
    # Register devices
    for i in range(2):
        client.post(
            f"/api/devices/{robot_id}/register",
            json={
                "device_type": "ROBOT_PRIMARY" if i == 0 else "SENSOR",
                "name": f"Device-{i}",
                "mac_address": f"00:1A:2B:3C:4D:{5E + i:02X}",
                "public_key": "-----BEGIN PUBLIC KEY-----\nMFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBALj...\n-----END PUBLIC KEY-----"
            }
        )
    
    # Get devices
    response = client.get(f"/api/devices/{robot_id}")
    assert response.status_code == 200
    devices = response.json()
    assert len(devices) == 2
