"""Robot management service"""

from typing import Optional, List
from uuid import uuid4
from sqlalchemy.orm import Session

from app.models.robot import (
    Robot,
    RobotStatus,
    Device,
    DeviceType,
    AuthenticationSession,
    AuthenticationStatus,
    LoginAttempt,
    DeviceFingerprint,
)
from app.schemas import RobotRegisterRequest, RobotResponse
from app.security.crypto import create_token_generator


class RobotService:
    """Service for robot management operations"""

    @staticmethod
    def register_robot(
        db: Session,
        request: RobotRegisterRequest,
    ) -> Robot:
        """
        Register a new robot in the system.
        
        Args:
            db: Database session
            request: Robot registration request
            
        Returns:
            Created Robot instance
            
        Raises:
            ValueError: If serial number already exists
        """
        # Check if serial number already exists
        existing = db.query(Robot).filter(
            Robot.serial_number == request.serial_number
        ).first()
        if existing:
            raise ValueError(f"Serial number {request.serial_number} already exists")
        
        # Generate unique robot_id
        robot_id = f"REX-{uuid4().hex[:12].upper()}"
        
        robot = Robot(
            robot_id=robot_id,
            name=request.name,
            model=request.model,
            serial_number=request.serial_number,
            firmware_version=request.firmware_version,
            description=request.description,
            location=request.location,
            metadata=request.metadata,
            status=RobotStatus.ACTIVE,
        )
        
        db.add(robot)
        db.commit()
        db.refresh(robot)
        
        return robot

    @staticmethod
    def get_robot_by_id(db: Session, robot_identifier: str) -> Optional[Robot]:
        """
        Get robot by robot_id or database id.
        
        Args:
            db: Database session
            robot_identifier: Robot ID (string or numeric)
            
        Returns:
            Robot instance or None
        """
        # Try to match robot_id (string identifier)
        robot = db.query(Robot).filter(Robot.robot_id == robot_identifier).first()
        if robot:
            return robot
        
        # Try to match by numeric ID
        try:
            robot_db_id = int(robot_identifier)
            robot = db.query(Robot).filter(Robot.id == robot_db_id).first()
            return robot
        except (ValueError, TypeError):
            pass
        
        return None

    @staticmethod
    def get_robot_by_serial(db: Session, serial_number: str) -> Optional[Robot]:
        """Get robot by serial number"""
        return db.query(Robot).filter(Robot.serial_number == serial_number).first()

    @staticmethod
    def list_robots(db: Session, skip: int = 0, limit: int = 100) -> List[Robot]:
        """List all robots with pagination"""
        return db.query(Robot).offset(skip).limit(limit).all()

    @staticmethod
    def update_robot_status(
        db: Session,
        robot: Robot,
        status: RobotStatus,
    ) -> Robot:
        """Update robot status"""
        robot.status = status
        if status == RobotStatus.ACTIVE:
            robot.activated_at = None
        elif status == RobotStatus.DEACTIVATED:
            from app.models.robot import utcnow
            robot.deactivated_at = utcnow()
        
        db.commit()
        db.refresh(robot)
        return robot

    @staticmethod
    def record_heartbeat(
        db: Session,
        robot: Robot,
    ) -> Robot:
        """
        Record a heartbeat from the robot.
        
        Args:
            db: Database session
            robot: Robot instance
            
        Returns:
            Updated Robot instance
        """
        from app.models.robot import utcnow
        robot.last_heartbeat_at = utcnow()
        db.commit()
        db.refresh(robot)
        return robot

    @staticmethod
    def deactivate_robot(db: Session, robot: Robot) -> Robot:
        """Deactivate a robot"""
        return RobotService.update_robot_status(db, robot, RobotStatus.DEACTIVATED)

    @staticmethod
    def activate_robot(db: Session, robot: Robot) -> Robot:
        """Activate a robot"""
        return RobotService.update_robot_status(db, robot, RobotStatus.ACTIVE)


class DeviceService:
    """Service for device management operations"""

    @staticmethod
    def register_device(
        db: Session,
        robot: Robot,
        device_type: DeviceType,
        name: str,
        mac_address: str,
        public_key: str,
    ) -> Device:
        """
        Register a new device for a robot.
        
        Args:
            db: Database session
            robot: Robot instance
            device_type: Type of device
            name: Device name
            mac_address: MAC address
            public_key: Device public key
            
        Returns:
            Created Device instance
            
        Raises:
            ValueError: If MAC address already exists
        """
        # Check if MAC address already exists
        existing = db.query(Device).filter(Device.mac_address == mac_address).first()
        if existing:
            raise ValueError(f"MAC address {mac_address} already registered")
        
        # Generate device_id
        device_id = f"DEV-{uuid4().hex[:12].upper()}"
        
        device = Device(
            device_id=device_id,
            robot_id=robot.id,
            device_type=device_type,
            name=name,
            mac_address=mac_address,
            public_key=public_key,
            is_active=True,
        )
        
        db.add(device)
        db.commit()
        db.refresh(device)
        
        return device

    @staticmethod
    def get_device_by_id(db: Session, device_identifier: str) -> Optional[Device]:
        """
        Get device by device_id or database id.
        
        Args:
            db: Database session
            device_identifier: Device ID (string or numeric)
            
        Returns:
            Device instance or None
        """
        # Try device_id
        device = db.query(Device).filter(Device.device_id == device_identifier).first()
        if device:
            return device
        
        # Try numeric ID
        try:
            device_db_id = int(device_identifier)
            device = db.query(Device).filter(Device.id == device_db_id).first()
            return device
        except (ValueError, TypeError):
            pass
        
        return None

    @staticmethod
    def get_devices_by_robot(db: Session, robot: Robot) -> List[Device]:
        """Get all devices for a robot"""
        return db.query(Device).filter(Device.robot_id == robot.id).all()

    @staticmethod
    def deactivate_device(db: Session, device: Device) -> Device:
        """Deactivate a device"""
        device.is_active = False
        from app.models.robot import utcnow
        device.deactivated_at = utcnow()
        db.commit()
        db.refresh(device)
        return device


class AuthenticationService:
    """Service for authentication operations"""

    @staticmethod
    def create_authentication_session(
        db: Session,
        robot: Robot,
        device: Optional[Device],
        access_token: str,
        refresh_token: str,
        access_token_jti: str,
        refresh_token_jti: str,
        fingerprint_hash: Optional[str],
        ip_address: Optional[str],
        user_agent: Optional[str],
        access_token_expires_at,
        refresh_token_expires_at,
    ) -> AuthenticationSession:
        """
        Create an authentication session.
        
        Args:
            db: Database session
            robot: Robot instance
            device: Optional Device instance
            access_token: Access token JWT
            refresh_token: Refresh token JWT
            access_token_jti: Access token JTI
            refresh_token_jti: Refresh token JTI
            fingerprint_hash: Device fingerprint hash
            ip_address: Client IP address
            user_agent: User agent string
            access_token_expires_at: Access token expiry time
            refresh_token_expires_at: Refresh token expiry time
            
        Returns:
            Created AuthenticationSession
        """
        session_id = str(uuid4())
        
        auth_session = AuthenticationSession(
            session_id=session_id,
            robot_id=robot.id,
            device_id=device.id if device else None,
            access_token_jti=access_token_jti,
            refresh_token_jti=refresh_token_jti,
            status=AuthenticationStatus.ACTIVE,
            ip_address=ip_address,
            user_agent=user_agent,
            fingerprint_hash=fingerprint_hash,
            access_token_expires_at=access_token_expires_at,
            refresh_token_expires_at=refresh_token_expires_at,
        )
        
        db.add(auth_session)
        db.commit()
        db.refresh(auth_session)
        
        return auth_session

    @staticmethod
    def get_session_by_jti(db: Session, jti: str) -> Optional[AuthenticationSession]:
        """Get authentication session by JTI"""
        return db.query(AuthenticationSession).filter(
            AuthenticationSession.access_token_jti == jti
        ).first()

    @staticmethod
    def revoke_session(db: Session, session: AuthenticationSession) -> AuthenticationSession:
        """Revoke an authentication session"""
        from app.models.robot import utcnow
        session.status = AuthenticationStatus.REVOKED
        session.revoked_at = utcnow()
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def record_login_attempt(
        db: Session,
        robot: Robot,
        ip_address: str,
        fingerprint_hash: Optional[str],
        success: bool,
        error_message: Optional[str] = None,
    ) -> LoginAttempt:
        """Record a login attempt for audit trail"""
        attempt = LoginAttempt(
            robot_id=robot.id,
            ip_address=ip_address,
            fingerprint_hash=fingerprint_hash,
            success=success,
            error_message=error_message,
        )
        
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
        
        return attempt
