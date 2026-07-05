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




# Robot Schemas
class RobotRegisterRequest(BaseModel):
    """Request model for robot registration"""
    name: str = Field(..., min_length=1, max_length=255, description="Robot name")
    model: str = Field(..., min_length=1, max_length=255, description="Robot model")
    serial_key: str = Field(..., min_length=1, max_length=255, description="Serial key")
    firmware_version: Optional[str] = Field(None, description="Firmware version")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "REX-001",
                "model": "REX-Pro-v2",
                "serial_key": "REX-SN-20240422-001",
                "firmware_version": "v1.2.0"
            }
        }


class RobotResponse(BaseModel):
    """Response model for robot data"""
    id: int
    robot_id: str
    name: str
    model: str
    firmware_version: Optional[str] = None
    status: RobotStatus
    created_at: datetime

    class Config:
        from_attributes = True


class RobotPairRequest(BaseModel):
    """Request model for pairing a robot"""
    robot_id: str = Field(..., description="Robot identifier")
    serial_key: str = Field(..., description="Serial key for the robot")
    user_id: str = Field(..., description="User ID pairing the robot")

class RobotUpdate(BaseModel):
    """Request model for updating a robot"""
    name: Optional[str] = None

class SuccessResponse(BaseModel):
    """Standard success response"""
    success: bool


class RobotHeartbeatRequest(BaseModel):
    """Request model for robot heartbeat"""
    robot_id: str = Field(..., description="Robot identifier")


# Error Response
class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "INVALID_CREDENTIALS",
                "message": "Invalid robot_id or secret_key",
                "details": {}
            }
        }
