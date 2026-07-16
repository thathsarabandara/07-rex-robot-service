from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.auth import get_current_robot_id
from app.schemas.configuration import RobotConfigurationResponse
from app.schemas.device_auth import (
    DeviceAuthenticateRequest,
    DeviceAuthenticateResponse,
    DeviceRefreshRequest,
)
from app.services.configuration_service import get_robot_configuration
from app.services.device_auth_service import (
    authenticate_device,
    refresh_device_token,
    revoke_device_session,
)

router = APIRouter(prefix="/device", tags=["Device Authentication"])

@router.post("/authenticate", response_model=DeviceAuthenticateResponse)
async def authenticate(
    request: Request,
    body: DeviceAuthenticateRequest,
    db: Session = Depends(get_db)
):
    """Authenticate a physical robot device using its credentials."""
    ip_address = request.client.host if request.client else None
    res = authenticate_device(
        db=db,
        robot_id=body.robot_id,
        robot_secret=body.robot_secret,
        firmware_version=body.firmware_version,
        ip_address=ip_address
    )
    return res

@router.post("/refresh", response_model=DeviceAuthenticateResponse)
async def refresh(
    request: Request,
    body: DeviceRefreshRequest,
    db: Session = Depends(get_db)
):
    """Refresh the robot JWT token session using refresh token."""
    ip_address = request.client.host if request.client else None
    res = refresh_device_token(
        db=db,
        refresh_token=body.refresh_token,
        ip_address=ip_address
    )
    return res

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    robot_id: str = Depends(get_current_robot_id),
    db: Session = Depends(get_db)
):
    """Revoke all device sessions for the authenticated robot."""
    revoke_device_session(db, robot_id)
    return None

@router.get("/config", response_model=RobotConfigurationResponse)
async def get_device_config(
    robot_id: str = Depends(get_current_robot_id),
    db: Session = Depends(get_db)
):
    """Retrieve configuration settings directly from robot device context."""
    config = get_robot_configuration(db, robot_id)
    return config
