import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config.database import Base, engine
from app.config.kafka import close_kafka, init_kafka
from app.config.settings import settings
from app.middleware.error_handler import exception_handler
from app.middleware.request_id import RequestIDMiddleware
from app.routes.claim import router as claim_router
from app.routes.configuration import router as configuration_router
from app.routes.control_lease import router as control_lease_router
from app.routes.device_auth import router as device_auth_router
from app.routes.emergency import router as emergency_router
from app.routes.events import router as events_router
from app.routes.health import metrics_router

# Import Routers
from app.routes.health import router as health_router
from app.routes.modes import router as modes_router
from app.routes.robots import router as robots_router
from app.routes.websockets import router as websockets_router
from app.services.mqtt_service import close_mqtt_client, init_mqtt_client
from app.workers.expired_command_worker import expired_commands_loop
from app.workers.heartbeat_monitor import monitor_heartbeats_loop
from app.workers.mqtt_consumer import run_mqtt_consumer

# Setup logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Track tasks to cancel them on shutdown
background_tasks: set[asyncio.Task] = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Lifespan events for starting/stopping background workers and connections."""
    logger.info("Initializing REX Robot Service application startup...")
    
    # Ensure MySQL tables exist (development/resilience fallback, Alembic manages migrations)
    if settings.APP_ENV != "test":
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables verified/created successfully.")
        except Exception as e:
            logger.error(f"Error checking/creating database tables: {e}")
            
    # Connect external services
    await init_mqtt_client()
    await init_kafka()
    
    # Spawn background worker loops
    if settings.APP_ENV != "test":
        task_mqtt = asyncio.create_task(run_mqtt_consumer())
        task_heartbeat = asyncio.create_task(monitor_heartbeats_loop())
        task_expired = asyncio.create_task(expired_commands_loop())
        
        background_tasks.add(task_mqtt)
        background_tasks.add(task_heartbeat)
        background_tasks.add(task_expired)
        
    yield
    
    # Shutdown events
    logger.info("Shutting down REX Robot Service application...")
    
    # Cancel background tasks
    for task in background_tasks:
        task.cancel()
        
    if background_tasks:
        await asyncio.gather(*background_tasks, return_exceptions=True)
        
    # Close connections
    await close_mqtt_client()
    await close_kafka()
    logger.info("Service shutdown completed successfully.")

def create_app() -> FastAPI:
    """FastAPI App Factory setup."""
    app = FastAPI(
        title=settings.APP_NAME,
        description="FastAPI Robot management and manual command routing service gateway.",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan
    )
    
    # Add CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Request ID middleware
    app.add_middleware(RequestIDMiddleware)
    
    # Exception Handler registrations
    app.add_exception_handler(RequestValidationError, exception_handler)
    app.add_exception_handler(StarletteHTTPException, exception_handler)
    app.add_exception_handler(Exception, exception_handler)
    
    # Register REST and WS routers
    FastAPI() # Secondary app or nested APIRouter mapping /api/v1
    
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(metrics_router, prefix="/api/v1")
    app.include_router(robots_router, prefix="/api/v1")
    app.include_router(claim_router, prefix="/api/v1")
    app.include_router(device_auth_router, prefix="/api/v1")
    app.include_router(configuration_router, prefix="/api/v1")
    app.include_router(modes_router, prefix="/api/v1")
    app.include_router(emergency_router, prefix="/api/v1")
    app.include_router(control_lease_router, prefix="/api/v1")
    app.include_router(events_router, prefix="/api/v1")
    app.include_router(websockets_router, prefix="/api/v1")
    
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )
