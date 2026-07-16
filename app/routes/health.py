from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("/live")
async def get_live():
    """Liveness probe."""
    return {"status": "ok"}

@router.get("/ready")
async def get_ready():
    """Readiness probe."""
    # Could check DB/Redis connectivity if desired, keeping it simple
    return {"status": "ready"}

metrics_router = APIRouter(tags=["Metrics"])

@metrics_router.get("/metrics")
async def get_metrics():
    """Prometheus metrics handler."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
