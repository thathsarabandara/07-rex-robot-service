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
    serial_number: str = Field(..., min_length=1, max_length=255, description="Serial number")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "REX-001",
                "model": "REX-Pro-v2",
                "serial_number": "REX-SN-20240422-001",
            }
        }


class RobotResponse(BaseModel):
    """Response model for robot data"""
    id: int
    robot_id: str
    name: str
    model: str
    serial_number: str
    owner_id: Optional[str] = None
    status: RobotStatus
    created_at: datetime

    class Config:
        from_attributes = True


class RobotClaimRequest(BaseModel):
    """Request model for claiming a robot"""
    robot_id: str = Field(..., description="Robot identifier")
    owner_id: str = Field(..., description="User ID to bind the robot to")


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
