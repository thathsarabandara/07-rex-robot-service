"""Device fingerprinting service"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.robot import Robot, Device, DeviceFingerprint
from app.security.fingerprint import DeviceFingerprintManager
from app.schemas import DeviceFingerprintRequest


class FingerprintService:
    """Service for device fingerprinting operations"""

    def __init__(self):
        self.fingerprint_manager = DeviceFingerprintManager()

    def register_fingerprint(
        self,
        db: Session,
        robot: Robot,
        device: Optional[Device],
        fingerprint_data: DeviceFingerprintRequest,
    ) -> DeviceFingerprint:
        """
        Register a new device fingerprint.
        
        Args:
            db: Database session
            robot: Robot instance
            device: Optional Device instance
            fingerprint_data: Fingerprint data
            
        Returns:
            Created DeviceFingerprint
            
        Raises:
            ValueError: If fingerprint already exists
        """
        # Extract and validate components
        components = self.fingerprint_manager.extract_fingerprint_components(
            fingerprint_data.model_dump()
        )
        
        # Generate fingerprint hash
        fingerprint_hash = self.fingerprint_manager.generate_fingerprint_hash(
            hardware_id=components["hardware_id"],
            mac_address=components["mac_address"],
            cpu_info=components["cpu_info"],
            os_info=components["os_info"],
            system_uuid=components["system_uuid"],
        )
        
        # Check if fingerprint already exists
        existing = db.query(DeviceFingerprint).filter(
            DeviceFingerprint.fingerprint_hash == fingerprint_hash
        ).first()
        if existing:
            raise ValueError("Fingerprint already registered")
        
        # Get fingerprint strength
        strength = self.fingerprint_manager.get_fingerprint_strength(components)
        
        fingerprint = DeviceFingerprint(
            fingerprint_hash=fingerprint_hash,
            robot_id=robot.id,
            device_id=device.id if device else None,
            hardware_id=components["hardware_id"],
            mac_address=components["mac_address"],
            cpu_info=components["cpu_info"],
            os_info=components["os_info"],
            system_uuid=components["system_uuid"],
            fingerprint_method=f"combined_{strength}",
            is_verified=False,
            verification_count=0,
        )
        
        db.add(fingerprint)
        db.commit()
        db.refresh(fingerprint)
        
        return fingerprint

    def get_fingerprint_by_hash(
        self,
        db: Session,
        fingerprint_hash: str,
    ) -> Optional[DeviceFingerprint]:
        """Get fingerprint by hash"""
        return db.query(DeviceFingerprint).filter(
            DeviceFingerprint.fingerprint_hash == fingerprint_hash
        ).first()

    def get_fingerprints_by_robot(
        self,
        db: Session,
        robot: Robot,
    ) -> list:
        """Get all fingerprints for a robot"""
        return db.query(DeviceFingerprint).filter(
            DeviceFingerprint.robot_id == robot.id
        ).all()

    def verify_fingerprint(
        self,
        db: Session,
        fingerprint: DeviceFingerprint,
        provided_data: DeviceFingerprintRequest,
    ) -> bool:
        """
        Verify a device fingerprint.
        
        Args:
            db: Database session
            fingerprint: DeviceFingerprint to verify
            provided_data: Provided fingerprint data
            
        Returns:
            True if fingerprint matches, False otherwise
        """
        components = self.fingerprint_manager.extract_fingerprint_components(
            provided_data.model_dump()
        )
        
        # Verify fingerprint
        is_valid = self.fingerprint_manager.verify_fingerprint(
            components,
            fingerprint.fingerprint_hash,
        )
        
        if is_valid:
            # Update verification count and timestamp
            from app.models.robot import utcnow
            fingerprint.verification_count += 1
            fingerprint.last_verified_at = utcnow()
            if fingerprint.verification_count == 1:
                fingerprint.is_verified = True
            db.commit()
            db.refresh(fingerprint)
        
        return is_valid

    def match_fingerprint_to_robot(
        self,
        db: Session,
        provided_data: DeviceFingerprintRequest,
    ) -> Optional[tuple]:
        """
        Match provided fingerprint to a registered robot.
        
        Args:
            db: Database session
            provided_data: Provided fingerprint data
            
        Returns:
            Tuple of (Robot, DeviceFingerprint) if match found, None otherwise
        """
        components = self.fingerprint_manager.extract_fingerprint_components(
            provided_data.model_dump()
        )
        
        # Generate hash for lookup
        test_hash = self.fingerprint_manager.generate_fingerprint_hash(
            hardware_id=components["hardware_id"],
            mac_address=components["mac_address"],
            cpu_info=components["cpu_info"],
            os_info=components["os_info"],
            system_uuid=components["system_uuid"],
        )
        
        # Find matching fingerprint
        fingerprint = db.query(DeviceFingerprint).filter(
            DeviceFingerprint.fingerprint_hash == test_hash
        ).first()
        
        if fingerprint:
            robot = db.query(Robot).filter(Robot.id == fingerprint.robot_id).first()
            return (robot, fingerprint)
        
        return None

    def delete_fingerprint(
        self,
        db: Session,
        fingerprint: DeviceFingerprint,
    ) -> None:
        """Delete a fingerprint"""
        db.delete(fingerprint)
        db.commit()
