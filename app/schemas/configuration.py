from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self


class RobotConfigurationResponse(BaseModel):
    robot_id: str
    version: int
    base_max_speed: int
    base_default_speed: int
    turn_speed: int
    acceleration_step: int
    braking_step: int
    joystick_dead_zone: float
    joystick_timeout_ms: int
    obstacle_stop_distance_cm: int
    arm_base_min_angle: int
    arm_base_max_angle: int
    arm_shoulder_min_angle: int
    arm_shoulder_max_angle: int
    arm_elbow_min_angle: int
    arm_elbow_max_angle: int
    arm_grip_min_angle: int
    arm_grip_max_angle: int
    arm_default_speed: int
    heartbeat_interval_seconds: int
    heartbeat_timeout_seconds: int
    telemetry_interval_ms: int
    buzzer_enabled: bool
    oled_eyes_enabled: bool
    automatic_night_light: bool

    class Config:
        from_attributes = True

class RobotConfigurationUpdateRequest(BaseModel):
    base_max_speed: int = Field(..., ge=0, le=100)
    base_default_speed: int = Field(..., ge=0, le=100)
    turn_speed: int = Field(..., ge=0, le=100)
    acceleration_step: int = Field(..., ge=1, le=50)
    braking_step: int = Field(..., ge=1, le=50)
    joystick_dead_zone: float = Field(..., ge=0.0, le=0.5)
    joystick_timeout_ms: int = Field(..., ge=100, le=5000)
    obstacle_stop_distance_cm: int = Field(..., ge=5, le=200)
    arm_base_min_angle: int = Field(..., ge=0, le=180)
    arm_base_max_angle: int = Field(..., ge=0, le=180)
    arm_shoulder_min_angle: int = Field(..., ge=0, le=180)
    arm_shoulder_max_angle: int = Field(..., ge=0, le=180)
    arm_elbow_min_angle: int = Field(..., ge=0, le=180)
    arm_elbow_max_angle: int = Field(..., ge=0, le=180)
    arm_grip_min_angle: int = Field(..., ge=0, le=180)
    arm_grip_max_angle: int = Field(..., ge=0, le=180)
    arm_default_speed: int = Field(..., ge=0, le=100)
    heartbeat_interval_seconds: int = Field(..., ge=1, le=60)
    heartbeat_timeout_seconds: int = Field(..., ge=2, le=300)
    telemetry_interval_ms: int = Field(..., ge=100, le=10000)
    buzzer_enabled: bool
    oled_eyes_enabled: bool
    automatic_night_light: bool

    @model_validator(mode="after")
    def validate_ranges(self) -> Self:
        # Validate base speed default is not above max
        if self.base_default_speed > self.base_max_speed:
            raise ValueError("base_default_speed cannot exceed base_max_speed")
        
        # Validate arm min/max angles
        if self.arm_base_min_angle > self.arm_base_max_angle:
            raise ValueError("arm_base_min_angle cannot exceed arm_base_max_angle")
        if self.arm_shoulder_min_angle > self.arm_shoulder_max_angle:
            raise ValueError("arm_shoulder_min_angle cannot exceed arm_shoulder_max_angle")
        if self.arm_elbow_min_angle > self.arm_elbow_max_angle:
            raise ValueError("arm_elbow_min_angle cannot exceed arm_elbow_max_angle")
        if self.arm_grip_min_angle > self.arm_grip_max_angle:
            raise ValueError("arm_grip_min_angle cannot exceed arm_grip_max_angle")
            
        # Heartbeat relation
        if self.heartbeat_timeout_seconds <= self.heartbeat_interval_seconds:
            raise ValueError("heartbeat_timeout_seconds must be greater than heartbeat_interval_seconds")
            
        return self
