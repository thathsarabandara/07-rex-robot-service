from typing import Literal

from pydantic import BaseModel, Field


class BaseJoystickMessage(BaseModel):
    type: Literal["BASE_JOYSTICK"]
    sequence: int
    x: float = Field(..., ge=-1.0, le=1.0)
    y: float = Field(..., ge=-1.0, le=1.0)
    speed_limit: int = Field(..., ge=0, le=100)
    timestamp: str

class BaseDirectionMessage(BaseModel):
    type: Literal["BASE_DIRECTION"]
    direction: Literal["FORWARD", "BACKWARD", "LEFT", "RIGHT", "STOP"]
    speed: int = Field(..., ge=0, le=100)
    duration_ms: int = Field(..., ge=0, le=10000)

class SpeedUpdateMessage(BaseModel):
    type: Literal["SPEED_UPDATE"]
    base_speed_limit: int = Field(..., ge=0, le=100)
    turn_speed: int = Field(..., ge=0, le=100)
    arm_speed: int = Field(..., ge=0, le=100)

class ArmJointMessage(BaseModel):
    type: Literal["ARM_JOINT"]
    joint: Literal["BASE", "SHOULDER", "ELBOW", "GRIP"]
    angle: int = Field(..., ge=0, le=180)
    speed: int = Field(..., ge=0, le=100)
    sequence: int

class ArmPoseJoints(BaseModel):
    base: int = Field(..., ge=0, le=180)
    shoulder: int = Field(..., ge=0, le=180)
    elbow: int = Field(..., ge=0, le=180)
    grip: int = Field(..., ge=0, le=180)

class ArmPoseMessage(BaseModel):
    type: Literal["ARM_POSE"]
    joints: ArmPoseJoints
    speed: int = Field(..., ge=0, le=100)
    sequence: int

class ArmStopMessage(BaseModel):
    type: Literal["ARM_STOP"]
