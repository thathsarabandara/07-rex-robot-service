"""Health check endpoint"""

from fastapi import APIRouter
from app.utils import success_response

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check():
    """Health check endpoint"""
    return success_response(
        data={"status": "healthy", "service": "rex-identity-server"},
        message="Service is healthy",
    )


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    return success_response(
        data={"ready": True},
        message="Service is ready",
    )
