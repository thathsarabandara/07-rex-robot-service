from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.device_session import RobotDeviceSession
from app.utils.tokens import decode_robot_jwt, decode_user_jwt

security = HTTPBearer(auto_error=False)

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Dependency that requires Bearer credentials and extracts user_id (sub)."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials are required"
        )
    payload = decode_user_jwt(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token"
        )
    return payload["sub"]

def get_current_user_id_ws(token: str | None = Query(None)) -> str:
    """Dependency that extracts user_id (sub) from query token for WebSockets."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token is required"
        )
    payload = decode_user_jwt(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token"
        )
    return payload["sub"]

def get_current_robot_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> str:
    """Dependency that requires Bearer credentials, extracts robot_id, and verifies active session."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials are required"
        )
    payload = decode_robot_jwt(credentials.credentials, expected_type="robot_access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired robot access token"
        )
    robot_id = payload["sub"]
    
    # Check if there is an active session
    active_session = db.query(RobotDeviceSession).filter(
        RobotDeviceSession.robot_id == robot_id,
        RobotDeviceSession.revoked_at.is_(None)
    ).first()
    
    if not active_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Robot session has been revoked or logged out"
        )
        
    return robot_id
