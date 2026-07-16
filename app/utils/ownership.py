from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.robot import Robot


def verify_robot_ownership(db: Session, robot_id: str, user_id: str) -> Robot:
    """Verify that a robot exists, is claimed, and belongs to the specified user."""
    robot = db.query(Robot).filter(Robot.id == robot_id).first()
    if not robot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Robot not found"
        )
    if robot.status != "CLAIMED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Robot is not claimed"
        )
    if robot.owner_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this robot"
        )
    return robot
