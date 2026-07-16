import asyncio
import logging

from app.config.database import SessionLocal
from app.services.command_service import expire_pending_commands

logger = logging.getLogger(__name__)

async def check_expired_commands():
    """Trigger command service database expiry check."""
    db = SessionLocal()
    try:
        expire_pending_commands(db)
    except Exception as e:
        logger.error(f"Error in expired command check: {e}")
    finally:
        db.close()

async def expired_commands_loop():
    """Background task runner for command expiration."""
    logger.info("Expired command cleanup task started")
    while True:
        try:
            await check_expired_commands()
        except Exception as e:
            logger.error(f"Error in expired commands loop: {e}")
        await asyncio.sleep(10)
