"""Device fingerprinting utilities for IoT device identification"""

import hashlib
import hmac
from typing import Dict, Optional
from datetime import datetime

from app.config import get_settings


class DeviceFingerprintManager:
    """Manages device fingerprint creation, verification, and hashing"""

    def __init__(self):
        self.settings = get_settings()
        self.algorithm = self.settings.fingerprint_algorithm
        self.salt = self.settings.device_fingerprint_salt.encode()

    def generate_fingerprint_hash(
        self,
        hardware_id: str,
        mac_address: str,
        cpu_info: str,
        os_info: str,
        system_uuid: str,
    ) -> str:
        """
        Generate a cryptographic hash of device fingerprint components.
        
        Args:
            hardware_id: Hardware identifier
            mac_address: MAC address
            cpu_info: CPU information
            os_info: Operating system information
            system_uuid: System UUID
            
        Returns:
            Hexadecimal fingerprint hash
        """
        # Normalize components
        components = [
            hardware_id.lower(),
            mac_address.lower(),
            cpu_info.lower(),
            os_info.lower(),
            system_uuid.lower(),
        ]
        
        # Create composite string
        composite = "|".join(components)
        
        # Generate HMAC
        fingerprint_hash = hmac.new(
            self.salt,
            composite.encode(),
            getattr(hashlib, self.algorithm),
        ).hexdigest()
        
        return fingerprint_hash

    def verify_fingerprint(
        self,
        provided_components: Dict[str, str],
        registered_hash: str,
    ) -> bool:
        """
        Verify provided fingerprint against registered hash.
        
        Args:
            provided_components: Dictionary with fingerprint components
            registered_hash: Hash to verify against
            
        Returns:
            True if fingerprint matches, False otherwise
        """
        computed_hash = self.generate_fingerprint_hash(
            hardware_id=provided_components.get("hardware_id", ""),
            mac_address=provided_components.get("mac_address", ""),
            cpu_info=provided_components.get("cpu_info", ""),
            os_info=provided_components.get("os_info", ""),
            system_uuid=provided_components.get("system_uuid", ""),
        )
        
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(computed_hash, registered_hash)

    def extract_fingerprint_components(
        self,
        fingerprint_data: Dict[str, str],
    ) -> Dict[str, str]:
        """
        Extract and validate fingerprint components.
        
        Args:
            fingerprint_data: Raw fingerprint data from client
            
        Returns:
            Validated fingerprint components
        """
        required_fields = [
            "hardware_id",
            "mac_address",
            "cpu_info",
            "os_info",
            "system_uuid",
        ]
        
        components = {}
        for field in required_fields:
            if field not in fingerprint_data or not fingerprint_data[field]:
                raise ValueError(f"Missing required field: {field}")
            components[field] = str(fingerprint_data[field]).strip()
        
        return components

    def is_fingerprint_unique(self, fingerprint_hash: str) -> bool:
        """
        Check if fingerprint hash is unique (not yet registered).
        
        Args:
            fingerprint_hash: Hash to check
            
        Returns:
            True if fingerprint is unique, False if already exists
        """
        # This would be checked against database
        # Implementation in service layer
        return True

    def get_fingerprint_strength(
        self,
        components: Dict[str, str],
    ) -> str:
        """
        Assess the strength of fingerprint components.
        
        Args:
            components: Fingerprint components
            
        Returns:
            Strength level: "STRONG", "MEDIUM", "WEAK"
        """
        score = 0
        
        # Check if all components have reasonable length
        if all(len(v) > 5 for v in components.values()):
            score += 1
        
        # Check if system_uuid looks like a valid UUID
        if len(components.get("system_uuid", "")) >= 36:
            score += 1
        
        # Check if MAC address is valid format
        mac = components.get("mac_address", "")
        if len(mac) >= 17 and (":" in mac or "-" in mac):
            score += 1
        
        if score >= 3:
            return "STRONG"
        elif score >= 2:
            return "MEDIUM"
        else:
            return "WEAK"


def create_device_fingerprint_manager() -> DeviceFingerprintManager:
    """Factory function to create fingerprint manager"""
    return DeviceFingerprintManager()
