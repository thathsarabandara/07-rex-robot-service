"""API routes module"""

from app.routes.health import router as health_router
from app.routes.robots import router as robots_router
from app.routes.devices import router as devices_router
from app.routes.auth import router as auth_router
from app.routes.fingerprints import router as fingerprints_router

__all__ = [
    "health_router",
    "robots_router",
    "devices_router",
    "auth_router",
    "fingerprints_router",
]
