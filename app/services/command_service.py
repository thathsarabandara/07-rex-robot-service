import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.robot_command import RobotCommand
from app.utils.dates import utc_now_naive

logger = logging.getLogger(__name__)

def create_command(
    db: Session,
    robot_id: str,
    issued_by_user_id: str | None,
    command_type: str,
    payload: dict | list | None,
    priority: int = 0,
    expires_at: datetime | None = None
) -> RobotCommand:
    """Create a persistent robot command in MySQL database."""
    cmd = RobotCommand(
        robot_id=robot_id,
        issued_by_user_id=issued_by_user_id,
        command_type=command_type,
        payload=payload,
        status="PENDING",
        priority=priority,
        expires_at=expires_at
    )
    db.add(cmd)
    db.commit()
    db.refresh(cmd)
    logger.info(f"Persistent command {cmd.id} created for robot {robot_id}")
    return cmd

def update_command_status(
    db: Session,
    command_id: str,
    status_str: str,
    failure_reason: str | None = None
) -> RobotCommand | None:
    """Update status of a persistent command."""
    cmd = db.query(RobotCommand).filter(RobotCommand.id == command_id).first()
    if not cmd:
        logger.warning(f"Attempted to update non-existent command {command_id}")
        return None
        
    cmd.status = status_str
    if failure_reason:
        cmd.failure_reason = failure_reason
        
    now = utc_now_naive()
    if status_str == "ACKNOWLEDGED":
        cmd.acknowledged_at = now
    elif status_str in ("COMPLETED", "FAILED", "REJECTED", "EXPIRED"):
        cmd.completed_at = now
        
    db.commit()
    db.refresh(cmd)
    logger.info(f"Persistent command {command_id} updated to status {status_str}")
    return cmd

def get_command_by_id(db: Session, command_id: str) -> RobotCommand | None:
    return db.query(RobotCommand).filter(RobotCommand.id == command_id).first()

def expire_pending_commands(db: Session) -> int:
    """Expire commands that are past their expiration date."""
    now = utc_now_naive()
    expired_cmds = db.query(RobotCommand).filter(
        RobotCommand.status.in_(["PENDING", "PUBLISHED"]),
        RobotCommand.expires_at.isnot(None),
        RobotCommand.expires_at < now
    ).all()
    
    count = 0
    for cmd in expired_cmds:
        cmd.status = "EXPIRED"
        cmd.completed_at = now
        count += 1
        
    if count > 0:
        db.commit()
        logger.info(f"Expired {count} pending/published commands")
        
    return count
