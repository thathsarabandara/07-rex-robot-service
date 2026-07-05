"""Robot management service"""

from typing import Optional, List
from uuid import uuid4
import hashlib
from sqlalchemy.orm import Session

from app.models.robot import Robot, RobotStatus
from app.models.robot_ownership import RobotOwnership
from app.schemas import RobotRegisterRequest, RobotPairRequest, RobotUpdate
from app.services.event_service import event_service


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
        hashed_key = hashlib.sha256(request.serial_key.encode()).hexdigest()

        # Check if serial key hash already exists
        existing = db.query(Robot).filter(
            Robot.serial_key_hash == hashed_key
        ).first()
        if existing:
            raise ValueError("Serial key already registered")
        
        # Generate unique robot_id if not provided, but request doesn't have it in Grabber it's provided?
        # Wait, in Rex the previous `register_robot` generated robot_id.
        robot_id = f"REX-{uuid4().hex[:12].upper()}"
        
        robot = Robot(
            robot_id=robot_id,
            name=request.name,
            model=request.model,
            serial_key_hash=hashed_key,
            firmware_version=request.firmware_version,
            status=RobotStatus.ACTIVE,
        )
        
        db.add(robot)
        db.commit()
        db.refresh(robot)
        
        return robot

    @staticmethod
    def pair_robot(db: Session, request: RobotPairRequest) -> Robot:
        """
        Pair a robot to a user.
        """
        # Check if robot exists
        robot = RobotService.get_robot_by_id(db, request.robot_id)
        if not robot:
            raise ValueError("Robot not found")
            
        hashed_pair_key = hashlib.sha256(request.serial_key.encode()).hexdigest()
        if robot.serial_key_hash != hashed_pair_key:
            raise ValueError("Invalid serial key")
            
        # Check if already paired
        ownership = db.query(RobotOwnership).filter(
            RobotOwnership.robot_id == robot.id
        ).first()
        
        if ownership:
            raise ValueError("Robot is already paired")
            
        new_ownership = RobotOwnership(
            robot_id=robot.id,
            user_id=request.user_id,
            role="OWNER"
        )
        db.add(new_ownership)
        db.commit()
        
        event_service.log_event(db, robot.id, "ROBOT_PAIRED", {"user_id": request.user_id})
        
        return robot

    @staticmethod
    def get_my_robots(db: Session, user_id: str) -> List[Robot]:
        """Get all robots owned by a user"""
        return db.query(Robot).join(RobotOwnership).filter(
            RobotOwnership.user_id == user_id
        ).all()

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
    def get_robot(db: Session, user_id: str, robot_identifier: str) -> Robot:
        """Get a specific robot ensuring ownership"""
        robot = RobotService.get_robot_by_id(db, robot_identifier)
        if not robot:
            raise ValueError("Robot not found")
            
        RobotService._check_ownership(db, user_id, robot.id)
        return robot

    @staticmethod
    def update_robot(db: Session, user_id: str, robot_identifier: str, update_data: RobotUpdate) -> Robot:
        """Update robot details"""
        robot = RobotService.get_robot_by_id(db, robot_identifier)
        if not robot:
            raise ValueError("Robot not found")
            
        RobotService._check_ownership(db, user_id, robot.id)
        
        if update_data.name is not None:
            robot.name = update_data.name
            
        db.add(robot)
        db.commit()
        db.refresh(robot)
        return robot

    @staticmethod
    def unpair_robot(db: Session, user_id: str, robot_identifier: str):
        """Unpair a robot from a user"""
        robot = RobotService.get_robot_by_id(db, robot_identifier)
        if not robot:
            raise ValueError("Robot not found")
            
        ownership = RobotService._check_ownership(db, user_id, robot.id)
        
        db.delete(ownership)
        db.commit()
        
        event_service.log_event(db, robot.id, "ROBOT_UNPAIRED", {"user_id": user_id})

    @staticmethod
    def _check_ownership(db: Session, user_id: str, robot_db_id: int) -> RobotOwnership:
        """Check if user owns the robot"""
        ownership = db.query(RobotOwnership).filter(
            RobotOwnership.robot_id == robot_db_id,
            RobotOwnership.user_id == user_id
        ).first()
        
        if not ownership:
            raise ValueError("Not authorized to access this robot")
            
        return ownership

    @staticmethod
    def list_robots(db: Session, skip: int = 0, limit: int = 100) -> List[Robot]:
        """List all robots with pagination"""
        return db.query(Robot).offset(skip).limit(limit).all()
