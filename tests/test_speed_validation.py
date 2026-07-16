from app.models.robot_configuration import RobotConfiguration
from app.utils.validation import apply_joystick_deadzone, clamp_speed, validate_joint_angle


def test_clamp_speed():
    assert clamp_speed(120, 100) == 100
    assert clamp_speed(-10, 80) == 0
    assert clamp_speed(50, 70) == 50

def test_apply_joystick_deadzone():
    # If deadzone is 0.05
    assert apply_joystick_deadzone(0.03, 0.05) == 0.0
    assert apply_joystick_deadzone(-0.02, 0.05) == 0.0
    assert apply_joystick_deadzone(0.1, 0.05) == 0.1
    assert apply_joystick_deadzone(-0.25, 0.05) == -0.25

def test_validate_joint_angles():
    config = RobotConfiguration(
        arm_base_min_angle=10,
        arm_base_max_angle=170,
        arm_shoulder_min_angle=20,
        arm_shoulder_max_angle=160,
        arm_elbow_min_angle=30,
        arm_elbow_max_angle=150,
        arm_grip_min_angle=5,
        arm_grip_max_angle=95
    )
    
    # Valid and clamped checks
    assert validate_joint_angle("BASE", 90, config) == 90
    assert validate_joint_angle("BASE", 5, config) == 10  # Clamped to min
    assert validate_joint_angle("BASE", 180, config) == 170 # Clamped to max
    
    assert validate_joint_angle("SHOULDER", 20, config) == 20
    assert validate_joint_angle("ELBOW", 160, config) == 150
    assert validate_joint_angle("GRIP", 100, config) == 95
