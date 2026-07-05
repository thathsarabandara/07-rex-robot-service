"""Robot management endpoints"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    RobotRegisterRequest, 
    RobotResponse, 
    RobotPairRequest, 
    RobotUpdate, 
    SuccessResponse
)
from app.services.robot_service import RobotService

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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/pair", response_model=SuccessResponse, status_code=200)
async def pair_robot(
    request: RobotPairRequest,
    db: Session = Depends(get_db),
):
    """Pair a robot for a user"""
    try:
        RobotService.pair_robot(db, request)
        return SuccessResponse(success=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/my", response_model=List[RobotResponse])
async def get_my_robots(
    x_user_id: str = Header(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """List all robots owned by the user"""
    try:
        robots = RobotService.get_my_robots(db, x_user_id)
        return robots
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{robot_identifier}", response_model=RobotResponse)
async def get_robot(
    robot_identifier: str,
    x_user_id: str = Header(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """Get robot details ensuring ownership"""
    try:
        robot = RobotService.get_robot(db, x_user_id, robot_identifier)
        return robot
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{robot_identifier}", response_model=RobotResponse)
async def update_robot(
    robot_identifier: str,
    update_data: RobotUpdate,
    x_user_id: str = Header(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """Update robot details"""
    try:
        robot = RobotService.update_robot(db, x_user_id, robot_identifier, update_data)
        return robot
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{robot_identifier}", status_code=204)
async def unpair_robot(
    robot_identifier: str,
    x_user_id: str = Header(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """Unpair a robot from a user"""
    try:
        RobotService.unpair_robot(db, x_user_id, robot_identifier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=List[RobotResponse])
async def list_robots(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all registered robots (Admin/Internal use)"""
    if skip < 0 or limit <= 0 or limit > 1000:
        raise HTTPException(status_code=400, detail="Invalid pagination parameters")
    
    robots = RobotService.list_robots(db, skip, limit)
    return robots
