"""API routes module"""

from app.routes.health import router as health_router
from app.routes.robots import router as robots_router

__all__ = [
    "health_router",
    "robots_router",
]
