import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.auth import get_current_user_id
from app.middleware.rate_limit import RateLimiter
from app.schemas.claim import ClaimRequest, ClaimResponse, CredentialsRotateResponse, UnpairResponse
from app.services.claim_service import claim_robot, unpair_robot
from app.services.kafka_service import publish_kafka_event
from app.utils.dates import utc_now_naive
from app.utils.ownership import verify_robot_ownership
from app.utils.secrets import generate_random_secret, hash_secret

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/robots", tags=["Claims"])

# Limit to 5 claim requests per minute per IP address to mitigate brute-forcing secrets
claim_limiter = RateLimiter(limit=5, window_seconds=60)

@router.post("/claim", response_model=ClaimResponse, dependencies=[Depends(claim_limiter)])
async def claim(
    request: ClaimRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Claim a physical robot using its ID and secret key."""
    robot = claim_robot(
        db=db,
        robot_id=request.robot_id,
        robot_secret=request.robot_secret,
        user_id=user_id
    )
    return {
        "message": "Robot claimed successfully",
        "robot": {
            "id": robot.id,
            "name": robot.name,
            "status": robot.status,
            "owner_user_id": robot.owner_user_id,
            "claimed_at": robot.claimed_at
        }
    }

@router.delete("/{robot_id}/claim", response_model=UnpairResponse)
async def unpair(
    robot_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Unpair/release ownership of a robot device."""
    robot = verify_robot_ownership(db, robot_id, user_id)
    unpair_robot(db, robot)
    return {
        "message": "Robot unpaired successfully",
        "robot_id": robot_id,
        "status": "UNCLAIMED"
    }

@router.post("/{robot_id}/credentials/rotate", response_model=CredentialsRotateResponse)
async def rotate_credentials(
    robot_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Rotate credentials of the robot. Returns new secret once."""
    robot = verify_robot_ownership(db, robot_id, user_id)
    
    new_raw_secret = generate_random_secret()
    robot.device_secret_hash = hash_secret(new_raw_secret)
    robot.secret_rotation_required = False
    robot.updated_at = utc_now_naive()
    db.commit()
    
    # Publish Kafka event
    import asyncio
    asyncio.create_task(publish_kafka_event(
        topic="rex.notification.robot.credentials-rotated.requested.v1",
        event_type="robot_credentials_rotated_notification",
        payload={
            "user_id": user_id,
            "robot_id": robot_id
        }
    ))
    
    return {
        "message": "Robot credentials rotated successfully",
        "robot_id": robot_id,
        "robot_secret": new_raw_secret
    }
