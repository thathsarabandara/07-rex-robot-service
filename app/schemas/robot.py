from datetime import datetime

from pydantic import BaseModel, Field


class RobotRegisterRequest(BaseModel):
    serial_number: str = Field(..., min_length=3, max_length=100)
    hardware_model: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)

class RobotRegisterResponse(BaseModel):
    robot_id: str
    robot_secret: str
    serial_number: str
    status: str

class RobotProfileUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=255)
    location_label: str | None = Field(None, max_length=100)

class RobotResponse(BaseModel):
    id: str
    owner_user_id: str | None
    serial_number: str
    hardware_model: str
    name: str
    description: str | None
    location_label: str | None
    firmware_version: str | None
    status: str
    connection_status: str
    current_mode: str
    emergency_stop_active: bool
    secret_rotation_required: bool
    last_seen_at: datetime | None
    claimed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
