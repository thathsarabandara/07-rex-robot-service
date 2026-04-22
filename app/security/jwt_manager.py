"""JWT token management and generation for robot authentication"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from uuid import uuid4

import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

from app.config import get_settings


class JWTTokenManager:
    """Manages JWT token creation, verification, and refresh"""

    def __init__(self):
        self.settings = get_settings()
        self.algorithm = self.settings.jwt_algorithm
        self.secret_key = self.settings.jwt_secret_key
        self.access_token_expires = self.settings.jwt_access_token_expires
        self.refresh_token_expires = self.settings.jwt_refresh_token_expires

    def create_access_token(
        self,
        robot_id: int,
        robot_identifier: str,
        device_id: Optional[int] = None,
        additional_claims: Optional[Dict] = None,
    ) -> Tuple[str, str, datetime]:
        """
        Create a JWT access token for a robot.
        
        Args:
            robot_id: Database robot ID
            robot_identifier: Human-readable robot identifier (robot_id)
            device_id: Optional device ID
            additional_claims: Additional claims to include in token
            
        Returns:
            Tuple of (token, jti, expiry_datetime)
        """
        jti = str(uuid4())
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.access_token_expires)
        
        payload = {
            "sub": str(robot_id),
            "robot_id": robot_identifier,
            "device_id": device_id,
            "type": "access",
            "jti": jti,
            "iat": now,
            "exp": expires_at,
            "iss": "rex-identity-server",
            "aud": "rex-services",
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        return token, jti, expires_at

    def create_refresh_token(
        self,
        robot_id: int,
        robot_identifier: str,
        session_id: str,
    ) -> Tuple[str, str, datetime]:
        """
        Create a JWT refresh token for a robot.
        
        Args:
            robot_id: Database robot ID
            robot_identifier: Human-readable robot identifier
            session_id: Authentication session ID
            
        Returns:
            Tuple of (token, jti, expiry_datetime)
        """
        jti = str(uuid4())
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.refresh_token_expires)
        
        payload = {
            "sub": str(robot_id),
            "robot_id": robot_identifier,
            "type": "refresh",
            "session_id": session_id,
            "jti": jti,
            "iat": now,
            "exp": expires_at,
            "iss": "rex-identity-server",
            "aud": "rex-services",
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        return token, jti, expires_at

    def verify_token(self, token: str) -> Dict:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Decoded token payload
            
        Raises:
            InvalidTokenError: If token is invalid
            ExpiredSignatureError: If token has expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": True},
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise ExpiredSignatureError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid token: {str(e)}")

    def extract_token_from_bearer(self, auth_header: Optional[str]) -> Optional[str]:
        """
        Extract JWT token from Bearer authorization header.
        
        Args:
            auth_header: Authorization header value
            
        Returns:
            Token if valid Bearer format, None otherwise
        """
        if not auth_header:
            return None
        
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        
        return parts[1]

    def decode_token_without_verification(self, token: str) -> Optional[Dict]:
        """
        Decode a token without verification (useful for debugging).
        Use with caution - never trust unverified tokens for authorization.
        
        Args:
            token: JWT token to decode
            
        Returns:
            Decoded payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=[self.algorithm],
            )
            return payload
        except Exception:
            return None

    def is_access_token(self, payload: Dict) -> bool:
        """Check if token payload is an access token"""
        return payload.get("type") == "access"

    def is_refresh_token(self, payload: Dict) -> bool:
        """Check if token payload is a refresh token"""
        return payload.get("type") == "refresh"

    def get_robot_id_from_token(self, payload: Dict) -> Optional[str]:
        """Extract robot_id from token payload"""
        return payload.get("robot_id")

    def get_device_id_from_token(self, payload: Dict) -> Optional[int]:
        """Extract device_id from token payload"""
        return payload.get("device_id")

    def get_jti_from_token(self, payload: Dict) -> Optional[str]:
        """Extract JTI (JWT ID) from token payload"""
        return payload.get("jti")


def create_jwt_token_manager() -> JWTTokenManager:
    """Factory function to create JWT token manager"""
    return JWTTokenManager()
