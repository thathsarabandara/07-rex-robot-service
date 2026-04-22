"""Authentication and JWT token endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.models.robot import Robot, RobotStatus
from app.schemas import (
    RobotLoginRequest,
    TokenResponse,
    TokenRefreshRequest,
    DeviceFingerprintRequest,
)
from app.services.robot_service import RobotService, DeviceService, AuthenticationService
from app.services.fingerprint_service import FingerprintService
from app.security.jwt_manager import create_jwt_token_manager
from app.utils import extract_ip_address, extract_user_agent, success_response, error_response

router = APIRouter(prefix="/auth", tags=["authentication"])

jwt_manager = create_jwt_token_manager()
fingerprint_service = FingerprintService()


@router.post("/login", response_model=TokenResponse)
async def robot_login(
    request_data: RobotLoginRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    """
    Authenticate a robot and issue JWT tokens.
    
    This endpoint performs the following:
    1. Verifies robot identity using fingerprint
    2. Validates device fingerprint
    3. Issues JWT access and refresh tokens
    4. Records authentication session
    """
    try:
        ip_address = await extract_ip_address(http_request)
        user_agent = extract_user_agent(http_request)
        
        # Get robot
        robot = RobotService.get_robot_by_id(db, request_data.robot_id)
        if not robot:
            # Record failed attempt
            AuthenticationService.record_login_attempt(
                db=db,
                robot=None,
                ip_address=ip_address,
                fingerprint_hash=None,
                success=False,
                error_message="Robot not found",
            )
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Check robot status
        if robot.status != RobotStatus.ACTIVE:
            AuthenticationService.record_login_attempt(
                db=db,
                robot=robot,
                ip_address=ip_address,
                fingerprint_hash=None,
                success=False,
                error_message=f"Robot status is {robot.status.value}",
            )
            raise HTTPException(status_code=403, detail="Robot is not active")
        
        # Get device if specified
        device = None
        if request_data.device_id:
            device = DeviceService.get_device_by_id(db, request_data.device_id)
            if not device or device.robot_id != robot.id:
                raise HTTPException(status_code=404, detail="Device not found")
        
        # Generate fingerprint hash
        fingerprint_hash = fingerprint_service.fingerprint_manager.generate_fingerprint_hash(
            hardware_id=request_data.fingerprint.hardware_id,
            mac_address=request_data.fingerprint.mac_address,
            cpu_info=request_data.fingerprint.cpu_info,
            os_info=request_data.fingerprint.os_info,
            system_uuid=request_data.fingerprint.system_uuid,
        )
        
        # Try to match fingerprint
        fingerprint_match = fingerprint_service.match_fingerprint_to_robot(
            db, request_data.fingerprint
        )
        
        if not fingerprint_match:
            # Fingerprint not recognized - try to register it
            try:
                fingerprint = fingerprint_service.register_fingerprint(
                    db, robot, device, request_data.fingerprint
                )
                AuthenticationService.record_login_attempt(
                    db=db,
                    robot=robot,
                    ip_address=ip_address,
                    fingerprint_hash=fingerprint_hash,
                    success=True,
                    error_message="New fingerprint registered",
                )
            except ValueError:
                # Fingerprint exists but for different robot
                AuthenticationService.record_login_attempt(
                    db=db,
                    robot=robot,
                    ip_address=ip_address,
                    fingerprint_hash=fingerprint_hash,
                    success=False,
                    error_message="Fingerprint mismatch",
                )
                raise HTTPException(
                    status_code=401,
                    detail="Device fingerprint mismatch",
                )
        else:
            matched_robot, matched_fingerprint = fingerprint_match
            if matched_robot.id != robot.id:
                AuthenticationService.record_login_attempt(
                    db=db,
                    robot=robot,
                    ip_address=ip_address,
                    fingerprint_hash=fingerprint_hash,
                    success=False,
                    error_message="Fingerprint belongs to different robot",
                )
                raise HTTPException(
                    status_code=401,
                    detail="Device fingerprint verification failed",
                )
        
        # Create JWT tokens
        access_token, access_jti, access_expires = jwt_manager.create_access_token(
            robot_id=robot.id,
            robot_identifier=robot.robot_id,
            device_id=device.id if device else None,
        )
        
        refresh_token, refresh_jti, refresh_expires = jwt_manager.create_refresh_token(
            robot_id=robot.id,
            robot_identifier=robot.robot_id,
            session_id=f"session-{robot.id}",
        )
        
        # Create authentication session
        auth_session = AuthenticationService.create_authentication_session(
            db=db,
            robot=robot,
            device=device,
            access_token=access_token,
            refresh_token=refresh_token,
            access_token_jti=access_jti,
            refresh_token_jti=refresh_jti,
            fingerprint_hash=fingerprint_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            access_token_expires_at=access_expires,
            refresh_token_expires_at=refresh_expires,
        )
        
        # Record successful login
        AuthenticationService.record_login_attempt(
            db=db,
            robot=robot,
            ip_address=ip_address,
            fingerprint_hash=fingerprint_hash,
            success=True,
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=jwt_manager.access_token_expires,
            refresh_expires_in=jwt_manager.refresh_token_expires,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.post("/refresh")
async def refresh_token(
    request_data: TokenRefreshRequest,
    db: Session = Depends(get_db),
):
    """
    Refresh JWT access token using refresh token.
    """
    try:
        # Verify refresh token
        payload = jwt_manager.verify_token(request_data.refresh_token)
        
        if not jwt_manager.is_refresh_token(payload):
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        # Get robot
        robot_id_str = payload.get("sub")
        robot_identifier = payload.get("robot_id")
        
        robot = RobotService.get_robot_by_id(db, robot_id_str)
        if not robot:
            raise HTTPException(status_code=401, detail="Robot not found")
        
        # Check robot status
        if robot.status != RobotStatus.ACTIVE:
            raise HTTPException(status_code=403, detail="Robot is not active")
        
        # Get old session using refresh token JTI
        refresh_jti = jwt_manager.get_jti_from_token(payload)
        old_session = db.query(type(AuthenticationService)).filter_by(
            refresh_token_jti=refresh_jti
        ).first()
        
        # Create new access token
        new_access_token, new_access_jti, new_access_expires = jwt_manager.create_access_token(
            robot_id=robot.id,
            robot_identifier=robot_identifier,
        )
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=request_data.refresh_token,
            token_type="Bearer",
            expires_in=jwt_manager.access_token_expires,
            refresh_expires_in=jwt_manager.refresh_token_expires,
        )
    
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token refresh failed: {str(e)}")


@router.post("/logout")
async def logout(
    http_request: Request,
    db: Session = Depends(get_db),
):
    """
    Logout robot and revoke authentication session.
    
    Requires valid Bearer token in Authorization header.
    """
    try:
        auth_header = http_request.headers.get("Authorization")
        token = jwt_manager.extract_token_from_bearer(auth_header)
        
        if not token:
            raise HTTPException(status_code=401, detail="Missing authentication token")
        
        # Verify token
        payload = jwt_manager.verify_token(token)
        
        if not jwt_manager.is_access_token(payload):
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        jti = jwt_manager.get_jti_from_token(payload)
        
        # Find and revoke session
        from app.models.robot import AuthenticationSession
        session = db.query(AuthenticationSession).filter_by(
            access_token_jti=jti
        ).first()
        
        if session:
            AuthenticationService.revoke_session(db, session)
        
        return success_response(
            data={"message": "Logged out successfully"},
            message="Logout successful",
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")
