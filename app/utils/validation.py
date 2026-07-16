from app.models.robot_configuration import RobotConfiguration


def apply_joystick_deadzone(value: float, dead_zone: float) -> float:
    """Apply joystick dead zone filter. If within dead zone, return 0.0."""
    if abs(value) < dead_zone:
        return 0.0
    return value

def clamp_speed(speed: int, max_speed: int) -> int:
    """Clamp speed value to the maximum allowed speed."""
    return min(max(0, speed), max_speed)

def validate_joint_angle(joint_name: str, angle: int, config: RobotConfiguration) -> int:
    """Validate joint angle against config limits, clamping to safe range."""
    joint = joint_name.upper()
    if joint == "BASE":
        min_angle, max_angle = config.arm_base_min_angle, config.arm_base_max_angle
    elif joint == "SHOULDER":
        min_angle, max_angle = config.arm_shoulder_min_angle, config.arm_shoulder_max_angle
    elif joint == "ELBOW":
        min_angle, max_angle = config.arm_elbow_min_angle, config.arm_elbow_max_angle
    elif joint == "GRIP":
        min_angle, max_angle = config.arm_grip_min_angle, config.arm_grip_max_angle
    else:
        raise ValueError(f"Unknown joint name: {joint_name}")
    
    return min(max(min_angle, angle), max_angle)
