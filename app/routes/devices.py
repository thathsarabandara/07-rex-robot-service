"""Device management endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.robot import DeviceType
from app.schemas import DeviceRegisterRequest, DeviceResponse
from app.services.robot_service import RobotService, DeviceService
from app.utils import success_response

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/{robot_identifier}/register", response_model=DeviceResponse, status_code=201)
async def register_device(
    robot_identifier: str,
    request: DeviceRegisterRequest,
    db: Session = Depends(get_db),
):
    """Register a new device for a robot"""
    robot = RobotService.get_robot_by_id(db, robot_identifier)
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    
    try:
        device = DeviceService.register_device(
            db=db,
            robot=robot,
            device_type=request.device_type,
            name=request.name,
            mac_address=request.mac_address,
            public_key=request.public_key,
        )
        return device
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Device registration failed: {str(e)}")


@router.get("/{robot_identifier}", response_model=list[DeviceResponse])
async def get_robot_devices(
    robot_identifier: str,
    db: Session = Depends(get_db),
):
    """Get all devices for a robot"""
    robot = RobotService.get_robot_by_id(db, robot_identifier)
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    
    devices = DeviceService.get_devices_by_robot(db, robot)
    return devices


@router.get("/detail/{device_identifier}", response_model=DeviceResponse)
async def get_device(
    device_identifier: str,
    db: Session = Depends(get_db),
):
    """Get device details by ID or device_id"""
    device = DeviceService.get_device_by_id(db, device_identifier)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.post("/{device_identifier}/deactivate")
async def deactivate_device(
    device_identifier: str,
    db: Session = Depends(get_db),
):
    """Deactivate a device"""
    device = DeviceService.get_device_by_id(db, device_identifier)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    try:
        device = DeviceService.deactivate_device(db, device)
        return success_response(
            data={"device_id": device.device_id, "is_active": device.is_active},
            message="Device deactivated successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
