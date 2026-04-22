"""Tests for robot management endpoints"""

import pytest
from app.schemas import RobotRegisterRequest


def test_register_robot(client):
    """Test robot registration"""
    response = client.post(
        "/api/robots/register",
        json={
            "name": "REX-001",
            "model": "REX-Pro-v2",
            "serial_number": "REX-SN-20240422-001",
            "firmware_version": "2.1.0",
            "description": "Home Assistant Robot",
            "location": "Living Room",
            "metadata": {"owner": "test_user"}
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "REX-001"
    assert data["robot_id"].startswith("REX-")
    assert data["status"] == "ACTIVE"


def test_register_duplicate_serial(client):
    """Test duplicate serial number registration"""
    robot_data = {
        "name": "REX-001",
        "model": "REX-Pro-v2",
        "serial_number": "REX-SN-20240422-001",
        "firmware_version": "2.1.0",
    }
    
    # First registration should succeed
    response1 = client.post("/api/robots/register", json=robot_data)
    assert response1.status_code == 201
    
    # Second registration with same serial should fail
    response2 = client.post("/api/robots/register", json=robot_data)
    assert response2.status_code == 409


def test_get_robot(client):
    """Test getting robot details"""
    # Register a robot first
    register_response = client.post(
        "/api/robots/register",
        json={
            "name": "REX-001",
            "model": "REX-Pro-v2",
            "serial_number": "REX-SN-20240422-001",
            "firmware_version": "2.1.0",
        }
    )
    
    robot_id = register_response.json()["robot_id"]
    
    # Get robot
    response = client.get(f"/api/robots/{robot_id}")
    assert response.status_code == 200
    assert response.json()["robot_id"] == robot_id


def test_list_robots(client):
    """Test listing robots"""
    # Register multiple robots
    for i in range(3):
        client.post(
            "/api/robots/register",
            json={
                "name": f"REX-{i:03d}",
                "model": "REX-Pro-v2",
                "serial_number": f"REX-SN-20240422-{i:03d}",
                "firmware_version": "2.1.0",
            }
        )
    
    # List robots
    response = client.get("/api/robots")
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_robot_heartbeat(client):
    """Test robot heartbeat"""
    # Register a robot
    register_response = client.post(
        "/api/robots/register",
        json={
            "name": "REX-001",
            "model": "REX-Pro-v2",
            "serial_number": "REX-SN-20240422-001",
            "firmware_version": "2.1.0",
        }
    )
    
    robot_id = register_response.json()["robot_id"]
    
    # Send heartbeat
    response = client.post(
        f"/api/robots/{robot_id}/heartbeat",
        json={
            "robot_id": robot_id,
            "status": "OPERATIONAL",
            "metadata": {"battery_level": 85}
        }
    )
    
    assert response.status_code == 200
    assert response.json()["success"] is True
