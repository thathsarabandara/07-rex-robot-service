"""Password hashing and cryptographic utilities"""

from passlib.context import CryptContext
import secrets
import hashlib
from typing import Optional


class PasswordHasher:
    """Password hashing using Argon2"""

    def __init__(self):
        self.context = CryptContext(
            schemes=["argon2"],
            deprecated="auto",
            argon2__time_cost=2,
            argon2__memory_cost=65536,
            argon2__parallelism=4,
        )

    def hash_password(self, password: str) -> str:
        """
        Hash a password using Argon2.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        return self.context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password
            
        Returns:
            True if passwords match, False otherwise
        """
        return self.context.verify(plain_password, hashed_password)

    def needs_rehash(self, hashed_password: str) -> bool:
        """
        Check if a hash needs to be regenerated.
        
        Args:
            hashed_password: Hashed password to check
            
        Returns:
            True if hash should be regenerated, False otherwise
        """
        return self.context.needs_update(hashed_password)


class TokenGenerator:
    """Generate cryptographically secure tokens"""

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """
        Generate a cryptographically secure random token.
        
        Args:
            length: Token length in bytes (default 32 = 256-bit)
            
        Returns:
            Hex-encoded random token
        """
        return secrets.token_hex(length)

    @staticmethod
    def generate_numeric_code(length: int = 6) -> str:
        """
        Generate a numeric code (e.g., for OTP).
        
        Args:
            length: Code length (default 6)
            
        Returns:
            Numeric code as string
        """
        return "".join(str(secrets.randbelow(10)) for _ in range(length))


class HashUtilities:
    """Cryptographic hashing utilities"""

    @staticmethod
    def hash_token(token: str, algorithm: str = "sha256") -> str:
        """
        Hash a token for secure storage.
        
        Args:
            token: Token to hash
            algorithm: Hashing algorithm (default sha256)
            
        Returns:
            Hex-encoded hash
        """
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(token.encode())
        return hash_obj.hexdigest()

    @staticmethod
    def hash_data(data: str, algorithm: str = "sha256") -> str:
        """
        Hash arbitrary data.
        
        Args:
            data: Data to hash
            algorithm: Hashing algorithm (default sha256)
            
        Returns:
            Hex-encoded hash
        """
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(data.encode())
        return hash_obj.hexdigest()


def create_password_hasher() -> PasswordHasher:
    """Factory function to create password hasher"""
    return PasswordHasher()


def create_token_generator() -> TokenGenerator:
    """Factory function to create token generator"""
    return TokenGenerator()
