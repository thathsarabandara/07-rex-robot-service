"""Application configuration settings"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration using environment variables"""

    # App settings
    app_name: str = "REX Identity Server"
    app_version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"

    # Database
    database_url: str = "postgresql://robot_user:robot_password@localhost:5432/rex_identity"
    sqlalchemy_echo: bool = True

    # JWT Configuration
    jwt_secret_key: str = "your-super-secret-jwt-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires: int = 3600  # 1 hour
    jwt_refresh_token_expires: int = 2592000  # 30 days

    # Device Fingerprinting
    device_fingerprint_salt: str = "your-device-fingerprint-salt-change-in-production"
    fingerprint_algorithm: str = "sha256"

    # Security
    argon2_time_cost: int = 2
    argon2_memory_cost: int = 65536
    argon2_parallelism: int = 4

    # API Settings
    api_title: str = "REX Robot Identity Server"
    api_version: str = "1.0.0"
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
