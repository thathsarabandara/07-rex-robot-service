import logging
from datetime import datetime, timedelta, timezone

import jwt

from app.config.settings import settings

logger = logging.getLogger(__name__)

def decode_user_jwt(token: str) -> dict | None:
    """Decode and validate a User JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.USER_JWT_SECRET_KEY,
            algorithms=[settings.USER_JWT_ALGORITHM],
            audience=settings.USER_JWT_AUDIENCE,
            issuer=settings.USER_JWT_ISSUER
        )
        # Check sub and email_verified
        if "sub" not in payload:
            logger.warning("User JWT missing sub claim")
            return None
        if not payload.get("email_verified", False):
            logger.warning("User JWT has email_verified=False")
            return None
        return payload
    except jwt.PyJWTError as e:
        logger.warning(f"User JWT decode failure: {e}")
        return None

def create_robot_tokens(robot_id: str) -> tuple[str, str, datetime, datetime]:
    """Generate robot access token and refresh token along with their expiry times."""
    now = datetime.now(timezone.utc)
    
    access_expires = now + timedelta(hours=settings.ROBOT_ACCESS_TOKEN_EXPIRE_HOURS)
    access_payload = {
        "sub": robot_id,
        "type": "robot_access",
        "iat": int(now.timestamp()),
        "exp": int(access_expires.timestamp())
    }
    access_token = jwt.encode(
        access_payload,
        settings.ROBOT_JWT_SECRET_KEY,
        algorithm=settings.ROBOT_JWT_ALGORITHM
    )

    refresh_expires = now + timedelta(days=settings.ROBOT_REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_payload = {
        "sub": robot_id,
        "type": "robot_refresh",
        "iat": int(now.timestamp()),
        "exp": int(refresh_expires.timestamp())
    }
    refresh_token = jwt.encode(
        refresh_payload,
        settings.ROBOT_JWT_SECRET_KEY,
        algorithm=settings.ROBOT_JWT_ALGORITHM
    )
    
    # Return naive datetimes for SQL insertion compatible with utc_now_naive
    return (
        access_token, 
        refresh_token, 
        access_expires.replace(tzinfo=None), 
        refresh_expires.replace(tzinfo=None)
    )

def decode_robot_jwt(token: str, expected_type: str = "robot_access") -> dict | None:
    """Decode and validate a Robot JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.ROBOT_JWT_SECRET_KEY,
            algorithms=[settings.ROBOT_JWT_ALGORITHM]
        )
        if payload.get("type") != expected_type:
            logger.warning(f"Robot JWT type mismatch: expected {expected_type}, got {payload.get('type')}")
            return None
        if "sub" not in payload:
            logger.warning("Robot JWT missing sub claim")
            return None
        return payload
    except jwt.PyJWTError as e:
        logger.warning(f"Robot JWT decode failure: {e}")
        return None
