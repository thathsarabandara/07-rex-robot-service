"""Robot management endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.robot import Robot
from app.schemas import RobotRegisterRequest, RobotResponse, RobotHeartbeatRequest
from app.services.robot_service import RobotService
from app.utils import extract_ip_address, success_response, error_response

router = APIRouter(prefix="/robots", tags=["robots"])


@router.post("/register", response_model=RobotResponse, status_code=201)
async def register_robot(
    request: RobotRegisterRequest,
    db: Session = Depends(get_db),
):
    """Register a new robot in the system"""
    try:
        robot = RobotService.register_robot(db, request)
        return robot
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.get("/{robot_identifier}", response_model=RobotResponse)
async def get_robot(
    robot_identifier: str,
    db: Session = Depends(get_db),
):
    """Get robot details by ID or robot_id"""
    robot = RobotService.get_robot_by_id(db, robot_identifier)
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    return robot


@router.get("", response_model=list[RobotResponse])
async def list_robots(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all registered robots"""
    if skip < 0 or limit <= 0 or limit > 1000:
        raise HTTPException(status_code=400, detail="Invalid pagination parameters")
    
    robots = RobotService.list_robots(db, skip, limit)
    return robots


@router.post("/{robot_identifier}/heartbeat")
async def robot_heartbeat(
    robot_identifier: str,
    request_data: RobotHeartbeatRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    """Record a heartbeat from robot"""
    robot = RobotService.get_robot_by_id(db, robot_identifier)
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    
    try:
        robot = RobotService.record_heartbeat(db, robot)
        return success_response(
            data={"robot_id": robot.robot_id, "last_heartbeat": robot.last_heartbeat_at},
            message="Heartbeat recorded successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Heartbeat recording failed: {str(e)}")


@router.post("/{robot_identifier}/activate")
async def activate_robot(
    robot_identifier: str,
    db: Session = Depends(get_db),
):
    """Activate a robot"""
    robot = RobotService.get_robot_by_id(db, robot_identifier)
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    
    try:
        robot = RobotService.activate_robot(db, robot)
        return success_response(
            data={"robot_id": robot.robot_id, "status": robot.status.value},
            message="Robot activated successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{robot_identifier}/deactivate")
async def deactivate_robot(
    robot_identifier: str,
    db: Session = Depends(get_db),
):
    """Deactivate a robot"""
    robot = RobotService.get_robot_by_id(db, robot_identifier)
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    
    try:
        robot = RobotService.deactivate_robot(db, robot)
        return success_response(
            data={"robot_id": robot.robot_id, "status": robot.status.value},
            message="Robot deactivated successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
