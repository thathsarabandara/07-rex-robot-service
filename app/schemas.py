"""Pydantic schema models for API requests and responses"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class RobotStatus(str, Enum):
    """Robot status enum"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    DEACTIVATED = "DEACTIVATED"


class DeviceType(str, Enum):
    """Device type enum"""
    ROBOT_PRIMARY = "ROBOT_PRIMARY"
    ROBOT_SECONDARY = "ROBOT_SECONDARY"
    SENSOR = "SENSOR"
    ACTUATOR = "ACTUATOR"
    EDGE_COMPUTE = "EDGE_COMPUTE"


# Robot Schemas
class RobotRegisterRequest(BaseModel):
    """Request model for robot registration"""
    name: str = Field(..., min_length=1, max_length=255, description="Robot name")
    model: str = Field(..., min_length=1, max_length=255, description="Robot model")
    serial_number: str = Field(..., min_length=1, max_length=255, description="Serial number")
    firmware_version: str = Field(..., min_length=1, max_length=50, description="Firmware version")
    description: Optional[str] = Field(None, max_length=1000, description="Robot description")
    location: Optional[str] = Field(None, max_length=255, description="Physical location")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "REX-001",
                "model": "REX-Pro-v2",
                "serial_number": "REX-SN-20240422-001",
                "firmware_version": "2.1.0",
                "description": "Home Assistant Robot",
                "location": "Living Room",
                "metadata": {"owner": "user123"}
            }
        }


class RobotResponse(BaseModel):
    """Response model for robot data"""
    id: int
    robot_id: str
    name: str
    model: str
    serial_number: str
    firmware_version: str
    status: RobotStatus
    description: Optional[str]
    location: Optional[str]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    last_heartbeat_at: Optional[datetime]
    activated_at: Optional[datetime]

    class Config:
        from_attributes = True


# Device Schemas
class DeviceRegisterRequest(BaseModel):
    """Request model for device registration"""
    device_type: DeviceType = Field(..., description="Type of device")
    name: str = Field(..., min_length=1, max_length=255, description="Device name")
    mac_address: str = Field(..., pattern=r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$", description="MAC address")
    public_key: str = Field(..., description="Public key for device")

    class Config:
        json_schema_extra = {
            "example": {
                "device_type": "ROBOT_PRIMARY",
                "name": "REX-PRIMARY-ETH0",
                "mac_address": "00:1A:2B:3C:4D:5E",
                "public_key": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
            }
        }


class DeviceResponse(BaseModel):
    """Response model for device data"""
    id: int
    device_id: str
    robot_id: int
    device_type: DeviceType
    name: str
    mac_address: str
    ip_address: Optional[str]
    is_active: bool
    created_at: datetime
    last_seen_at: Optional[datetime]

    class Config:
        from_attributes = True


# Device Fingerprint Schemas
class DeviceFingerprintRequest(BaseModel):
    """Request model for device fingerprinting"""
    hardware_id: str = Field(..., description="Hardware identifier")
    mac_address: str = Field(..., pattern=r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$", description="MAC address")
    cpu_info: str = Field(..., description="CPU information")
    os_info: str = Field(..., description="Operating system information")
    system_uuid: str = Field(..., description="System UUID")

    class Config:
        json_schema_extra = {
            "example": {
                "hardware_id": "hw-001",
                "mac_address": "00:1A:2B:3C:4D:5E",
                "cpu_info": "ARM Cortex-A72",
                "os_info": "Ubuntu 22.04 LTS",
                "system_uuid": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class DeviceFingerprintResponse(BaseModel):
    """Response model for device fingerprint"""
    id: int
    fingerprint_hash: str
    robot_id: int
    device_id: Optional[int]
    hardware_id: str
    mac_address: str
    cpu_info: str
    os_info: str
    system_uuid: str
    fingerprint_method: str
    is_verified: bool
    verification_count: int
    created_at: datetime
    last_verified_at: Optional[datetime]

    class Config:
        from_attributes = True


# Authentication Schemas
class RobotLoginRequest(BaseModel):
    """Request model for robot login"""
    robot_id: str = Field(..., description="Robot identifier")
    device_id: Optional[str] = Field(None, description="Device identifier")
    fingerprint: DeviceFingerprintRequest = Field(..., description="Device fingerprint")
    ip_address: Optional[str] = Field(None, description="Client IP address")

    class Config:
        json_schema_extra = {
            "example": {
                "robot_id": "REX-001",
                "device_id": "DEV-001",
                "fingerprint": {
                    "hardware_id": "hw-001",
                    "mac_address": "00:1A:2B:3C:4D:5E",
                    "cpu_info": "ARM Cortex-A72",
                    "os_info": "Ubuntu 22.04 LTS",
                    "system_uuid": "550e8400-e29b-41d4-a716-446655440000"
                },
                "ip_address": "192.168.1.100"
            }
        }


class TokenResponse(BaseModel):
    """Response model for token issuance"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("Bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    refresh_expires_in: int = Field(..., description="Refresh token expiry in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_expires_in": 2592000
            }
        }


class AuthenticationSessionResponse(BaseModel):
    """Response model for authentication session"""
    session_id: str
    robot_id: int
    status: str
    created_at: datetime
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime

    class Config:
        from_attributes = True


class TokenRefreshRequest(BaseModel):
    """Request model for token refresh"""
    refresh_token: str = Field(..., description="Refresh token")


class RobotHeartbeatRequest(BaseModel):
    """Request model for robot heartbeat"""
    robot_id: str = Field(..., description="Robot identifier")
    status: Optional[str] = Field(None, description="Current robot status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Robot status data")

    class Config:
        json_schema_extra = {
            "example": {
                "robot_id": "REX-001",
                "status": "OPERATIONAL",
                "metadata": {
                    "battery_level": 85,
                    "cpu_usage": 45,
                    "memory_usage": 60
                }
            }
        }


# Error Response
class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "INVALID_FINGERPRINT",
                "message": "Device fingerprint does not match registered fingerprint",
                "details": {"registered": "hash1", "provided": "hash2"}
            }
        }
