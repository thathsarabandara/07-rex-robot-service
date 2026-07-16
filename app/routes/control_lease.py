import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.auth import get_current_user_id
from app.services.control_lease_service import (
    acquire_control_lease,
    get_control_lease_status,
    release_control_lease,
)
from app.utils.ownership import verify_robot_ownership

router = APIRouter(prefix="/robots", tags=["Control Lease"])

class LeaseAcquireRequest(BaseModel):
    control_channel: Literal["WEB", "MOBILE", "BLE", "AUTONOMOUS"]
    connection_id: str | None = None

class LeaseReleaseRequest(BaseModel):
    connection_id: str

@router.post("/{robot_id}/control/acquire", status_code=status.HTTP_200_OK)
async def acquire_lease(
    robot_id: str,
    body: LeaseAcquireRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Acquire manual control lease over the robot."""
    verify_robot_ownership(db, robot_id, user_id)
    
    conn_id = body.connection_id or str(uuid.uuid4())
    success = await acquire_control_lease(
        robot_id=robot_id,
        user_id=user_id,
        connection_id=conn_id,
        control_channel=body.control_channel
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Robot control lease is already held by another controller"
        )
        
    status_info = await get_control_lease_status(robot_id)
    return {
        "acquired": True,
        "connection_id": conn_id,
        "control_channel": body.control_channel,
        "expires_at": status_info["expires_at"] if status_info else None
    }

@router.delete("/{robot_id}/control/release", status_code=status.HTTP_200_OK)
async def release_lease(
    robot_id: str,
    connection_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Release manual control lease over the robot."""
    verify_robot_ownership(db, robot_id, user_id)
    success = await release_control_lease(
        robot_id=robot_id,
        user_id=user_id,
        connection_id=connection_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lease release failed. Check if lease exists or is owned by you"
        )
        
    return {"released": True}

@router.get("/{robot_id}/control/status", status_code=status.HTTP_200_OK)
async def get_lease(
    robot_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get active control lease status."""
    verify_robot_ownership(db, robot_id, user_id)
    status_info = await get_control_lease_status(robot_id)
    if not status_info:
        return {"leased": False, "lease": None}
    return {
        "leased": True,
        "lease": status_info
    }
