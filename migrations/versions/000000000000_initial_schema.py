"""Initial schema

Revision ID: 000000000000
Revises: 
Create Date: 2026-07-15 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '000000000000'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Robots table
    op.create_table(
        'robots',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('owner_user_id', sa.String(length=36), nullable=True),
        sa.Column('serial_number', sa.String(length=100), nullable=False),
        sa.Column('hardware_model', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('location_label', sa.String(length=100), nullable=True),
        sa.Column('device_secret_hash', sa.String(length=255), nullable=False),
        sa.Column('firmware_version', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='UNCLAIMED'),
        sa.Column('connection_status', sa.String(length=50), nullable=False, server_default='OFFLINE'),
        sa.Column('current_mode', sa.String(length=50), nullable=False, server_default='IDLE'),
        sa.Column('emergency_stop_active', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('secret_rotation_required', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.Column('claimed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_robots_owner_user_id'), 'robots', ['owner_user_id'], unique=False)
    op.create_index(op.f('ix_robots_serial_number'), 'robots', ['serial_number'], unique=True)

    # 2. Robot Configurations table
    op.create_table(
        'robot_configurations',
        sa.Column('robot_id', sa.String(length=36), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('base_max_speed', sa.Integer(), nullable=False),
        sa.Column('base_default_speed', sa.Integer(), nullable=False),
        sa.Column('turn_speed', sa.Integer(), nullable=False),
        sa.Column('acceleration_step', sa.Integer(), nullable=False),
        sa.Column('braking_step', sa.Integer(), nullable=False),
        sa.Column('joystick_dead_zone', sa.Float(), nullable=False),
        sa.Column('joystick_timeout_ms', sa.Integer(), nullable=False),
        sa.Column('obstacle_stop_distance_cm', sa.Integer(), nullable=False),
        sa.Column('arm_base_min_angle', sa.Integer(), nullable=False),
        sa.Column('arm_base_max_angle', sa.Integer(), nullable=False),
        sa.Column('arm_shoulder_min_angle', sa.Integer(), nullable=False),
        sa.Column('arm_shoulder_max_angle', sa.Integer(), nullable=False),
        sa.Column('arm_elbow_min_angle', sa.Integer(), nullable=False),
        sa.Column('arm_elbow_max_angle', sa.Integer(), nullable=False),
        sa.Column('arm_grip_min_angle', sa.Integer(), nullable=False),
        sa.Column('arm_grip_max_angle', sa.Integer(), nullable=False),
        sa.Column('arm_default_speed', sa.Integer(), nullable=False),
        sa.Column('heartbeat_interval_seconds', sa.Integer(), nullable=False),
        sa.Column('heartbeat_timeout_seconds', sa.Integer(), nullable=False),
        sa.Column('telemetry_interval_ms', sa.Integer(), nullable=False),
        sa.Column('buzzer_enabled', sa.Boolean(), nullable=False),
        sa.Column('oled_eyes_enabled', sa.Boolean(), nullable=False),
        sa.Column('automatic_night_light', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['robot_id'], ['robots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('robot_id')
    )

    # 3. Robot Device Sessions table
    op.create_table(
        'robot_device_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('robot_id', sa.String(length=36), nullable=False),
        sa.Column('refresh_token_hash', sa.String(length=255), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('firmware_version', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(), nullable=False),
        sa.Column('access_expires_at', sa.DateTime(), nullable=False),
        sa.Column('refresh_expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['robot_id'], ['robots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. Robot Commands table
    op.create_table(
        'robot_commands',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('robot_id', sa.String(length=36), nullable=False),
        sa.Column('issued_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('command_type', sa.String(length=100), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('failure_reason', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['robot_id'], ['robots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. Robot Events table
    op.create_table(
        'robot_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('robot_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=False, server_default='INFO'),
        sa.Column('message', sa.String(length=255), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['robot_id'], ['robots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('robot_events')
    op.drop_table('robot_commands')
    op.drop_table('robot_device_sessions')
    op.drop_table('robot_configurations')
    op.drop_index(op.f('ix_robots_serial_number'), table_name='robots')
    op.drop_index(op.f('ix_robots_owner_user_id'), table_name='robots')
    op.drop_table('robots')
