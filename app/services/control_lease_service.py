import logging
import time
from typing import Mapping

from app.config.redis import redis_client
from app.config.settings import settings

logger = logging.getLogger(__name__)

def get_lease_key(robot_id: str) -> str:
    return f"robot:control_lease:{robot_id}"

async def acquire_control_lease(
    robot_id: str,
    user_id: str,
    connection_id: str,
    control_channel: str,
    duration_seconds: int | None = None
) -> bool:
    """Acquire or renew the control lease for a robot in Redis.
    Returns True if acquired/renewed successfully, False otherwise.
    """
    if duration_seconds is None:
        duration_seconds = settings.CONTROL_LEASE_EXPIRE_SECONDS

    key = get_lease_key(robot_id)
    existing = await redis_client.hgetall(key)
    
    now = time.time()
    
    if existing:
        # Check if existing lease is still valid and held by someone else
        existing_user = existing.get("user_id")
        existing_conn = existing.get("connection_id")
        
        # If it's held by another client, check if it's expired (in case TTL didn't trigger, or logic check)
        if existing_user != user_id or existing_conn != connection_id:
            # Check expiry field just in case
            expires_at = float(existing.get("expires_at", 0))
            if now < expires_at:
                logger.warning(f"Lease conflict for robot {robot_id}: active lease held by {existing_user}")
                return False
                
    # Set/Renew lease
    expires_at = now + duration_seconds
    lease_data: Mapping[str | bytes, bytes | float | int | str] = {
        "robot_id": robot_id,
        "user_id": user_id,
        "connection_id": connection_id,
        "control_channel": control_channel,
        "expires_at": str(expires_at)
    }
    
    async with redis_client.pipeline(transaction=True) as pipe:
        pipe.hset(key, mapping=lease_data)
        pipe.expire(key, duration_seconds)
        await pipe.execute()
        
    logger.info(f"Control lease acquired for robot {robot_id} by user {user_id}")
    return True

async def release_control_lease(robot_id: str, user_id: str, connection_id: str) -> bool:
    """Release the control lease if held by the calling client."""
    key = get_lease_key(robot_id)
    existing = await redis_client.hgetall(key)
    
    if not existing:
        return True
        
    if existing.get("user_id") == user_id and existing.get("connection_id") == connection_id:
        await redis_client.delete(key)
        logger.info(f"Control lease released for robot {robot_id}")
        return True
        
    return False

async def get_control_lease_status(robot_id: str) -> dict | None:
    """Get active control lease details or None if no active lease."""
    key = get_lease_key(robot_id)
    existing = await redis_client.hgetall(key)
    if not existing:
        return None
        
    # Double check expiry
    expires_at = float(existing.get("expires_at", 0))
    if time.time() > expires_at:
        await redis_client.delete(key)
        return None
        
    return {
        "robot_id": existing.get("robot_id"),
        "user_id": existing.get("user_id"),
        "connection_id": existing.get("connection_id"),
        "control_channel": existing.get("control_channel"),
        "expires_at": expires_at
    }

async def is_lease_owner(robot_id: str, user_id: str, connection_id: str) -> bool:
    """Verify if the user and connection holds the active control lease."""
    status = await get_control_lease_status(robot_id)
    if not status:
        return False
    return status["user_id"] == user_id and status["connection_id"] == connection_id
