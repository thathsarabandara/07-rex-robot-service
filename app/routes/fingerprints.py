"""Fingerprinting endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import DeviceFingerprintRequest, DeviceFingerprintResponse
from app.services.robot_service import RobotService, DeviceService
from app.services.fingerprint_service import FingerprintService
from app.utils import success_response

router = APIRouter(prefix="/fingerprints", tags=["fingerprints"])
fingerprint_service = FingerprintService()


@router.post("/register/{robot_identifier}", response_model=DeviceFingerprintResponse, status_code=201)
async def register_fingerprint(
    robot_identifier: str,
    request: DeviceFingerprintRequest,
    db: Session = Depends(get_db),
):
    """Register a new device fingerprint for a robot"""
    robot = RobotService.get_robot_by_id(db, robot_identifier)
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    
    try:
        fingerprint = fingerprint_service.register_fingerprint(
            db=db,
            robot=robot,
            device=None,
            fingerprint_data=request,
        )
        return fingerprint
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fingerprint registration failed: {str(e)}")


@router.get("/{robot_identifier}", response_model=list[DeviceFingerprintResponse])
async def get_robot_fingerprints(
    robot_identifier: str,
    db: Session = Depends(get_db),
):
    """Get all fingerprints for a robot"""
    robot = RobotService.get_robot_by_id(db, robot_identifier)
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    
    fingerprints = fingerprint_service.get_fingerprints_by_robot(db, robot)
    return fingerprints


@router.get("/detail/{fingerprint_hash}", response_model=DeviceFingerprintResponse)
async def get_fingerprint(
    fingerprint_hash: str,
    db: Session = Depends(get_db),
):
    """Get fingerprint details by hash"""
    fingerprint = fingerprint_service.get_fingerprint_by_hash(db, fingerprint_hash)
    if not fingerprint:
        raise HTTPException(status_code=404, detail="Fingerprint not found")
    return fingerprint


@router.post("/verify/{robot_identifier}")
async def verify_device_fingerprint(
    robot_identifier: str,
    request: DeviceFingerprintRequest,
    db: Session = Depends(get_db),
):
    """Verify a device fingerprint"""
    robot = RobotService.get_robot_by_id(db, robot_identifier)
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    
    try:
        fingerprints = fingerprint_service.get_fingerprints_by_robot(db, robot)
        
        if not fingerprints:
            raise HTTPException(status_code=404, detail="No fingerprints registered for robot")
        
        # Try to verify against first fingerprint (most recent)
        fingerprint = fingerprints[0]
        is_valid = fingerprint_service.verify_fingerprint(db, fingerprint, request)
        
        return success_response(
            data={"is_valid": is_valid, "fingerprint_hash": fingerprint.fingerprint_hash},
            message="Fingerprint verification completed",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


@router.post("/strength")
async def check_fingerprint_strength(
    request: DeviceFingerprintRequest,
):
    """Check the strength of fingerprint components"""
    try:
        components = fingerprint_service.fingerprint_manager.extract_fingerprint_components(
            request.model_dump()
        )
        strength = fingerprint_service.fingerprint_manager.get_fingerprint_strength(components)
        
        return success_response(
            data={"strength": strength},
            message="Fingerprint strength evaluated",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
