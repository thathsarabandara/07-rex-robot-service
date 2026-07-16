from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.auth import get_current_user_id
from app.schemas.robot import (
    RobotProfileUpdateRequest,
    RobotRegisterRequest,
    RobotRegisterResponse,
    RobotResponse,
)
from app.services.robot_service import get_user_robots, register_robot, update_robot_profile
from app.utils.ownership import verify_robot_ownership

router = APIRouter(prefix="/robots", tags=["Robots"])

@router.post("/register", response_model=RobotRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RobotRegisterRequest, 
    user_id: str = Depends(get_current_user_id), 
    db: Session = Depends(get_db)
):
    """Register/provision a new physical robot device."""
    robot, raw_secret = register_robot(
        db=db,
        serial_number=request.serial_number,
        hardware_model=request.hardware_model,
        name=request.name
    )
    return {
        "robot_id": robot.id,
        "robot_secret": raw_secret,
        "serial_number": robot.serial_number,
        "status": robot.status
    }

@router.get("", response_model=list[RobotResponse])
async def list_robots(
    user_id: str = Depends(get_current_user_id), 
    db: Session = Depends(get_db)
):
    """List robots claimed/owned by the authenticated user."""
    return get_user_robots(db, user_id)

@router.get("/{robot_id}", response_model=RobotResponse)
async def get_robot(
    robot_id: str, 
    user_id: str = Depends(get_current_user_id), 
    db: Session = Depends(get_db)
):
    """Retrieve details of a specific owned robot."""
    robot = verify_robot_ownership(db, robot_id, user_id)
    return robot

@router.patch("/{robot_id}", response_model=RobotResponse)
async def patch_robot(
    robot_id: str,
    request: RobotProfileUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Update name, description, or location label of a claimed robot."""
    robot = verify_robot_ownership(db, robot_id, user_id)
    updated = update_robot_profile(
        db=db,
        robot=robot,
        name=request.name,
        description=request.description,
        location_label=request.location_label
    )
    return updated
