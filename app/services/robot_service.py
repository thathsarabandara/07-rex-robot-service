"""Robot management service"""

from typing import Optional, List
from uuid import uuid4
from sqlalchemy.orm import Session

from app.models.robot import (
    Robot,
    RobotStatus,
)
from app.schemas import RobotRegisterRequest


class RobotService:
    """Service for robot management operations"""

    @staticmethod
    def register_robot(
        db: Session,
        request: RobotRegisterRequest,
    ) -> Robot:
        """
        Register a new robot in the system.
        """
        # Check if serial number already exists
        existing = db.query(Robot).filter(
            Robot.serial_number == request.serial_number
        ).first()
        if existing:
            raise ValueError(f"Serial number {request.serial_number} already exists")
        
        # Generate unique robot_id
        robot_id = f"REX-{uuid4().hex[:12].upper()}"
        
        robot = Robot(
            robot_id=robot_id,
            name=request.name,
            model=request.model,
            serial_number=request.serial_number,
            status=RobotStatus.ACTIVE,
        )
        
        db.add(robot)
        db.commit()
        db.refresh(robot)
        
        return robot

    @staticmethod
    def get_robot_by_id(db: Session, robot_identifier: str) -> Optional[Robot]:
        """
        Get robot by robot_id or database id.
        """
        # Try to match robot_id (string identifier)
        robot = db.query(Robot).filter(Robot.robot_id == robot_identifier).first()
        if robot:
            return robot
        
        # Try to match by numeric ID
        try:
            robot_db_id = int(robot_identifier)
            robot = db.query(Robot).filter(Robot.id == robot_db_id).first()
            return robot
        except (ValueError, TypeError):
            pass
        
        return None

    @staticmethod
    def list_robots(db: Session, skip: int = 0, limit: int = 100) -> List[Robot]:
        """List all robots with pagination"""
        return db.query(Robot).offset(skip).limit(limit).all()

    @staticmethod
    def claim_robot(db: Session, robot_id: str, owner_id: str) -> Robot:
        """
        Bind a robot to a user.
        """
        robot = RobotService.get_robot_by_id(db, robot_id)
        if not robot:
            raise ValueError("Robot not found")
        
        if robot.owner_id:
            raise ValueError("Robot is already claimed")
            
        robot.owner_id = owner_id
        db.commit()
        db.refresh(robot)
        return robot
