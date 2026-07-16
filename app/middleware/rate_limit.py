import logging
import time

from fastapi import HTTPException, Request

from app.config.redis import redis_client

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds

    async def __call__(self, request: Request):
        if redis_client is None:
            logger.warning("Redis is not initialized or offline. Rate limiter bypassed.")
            return

        ip = request.client.host if request.client else "unknown"
        path = request.url.path
        key = f"rate_limit:{ip}:{path}"

        try:
            now = time.time()
            async with redis_client.pipeline(transaction=True) as pipe:
                pipe.zremrangebyscore(key, 0, now - self.window_seconds)
                pipe.zcard(key)
                pipe.zadd(key, {str(now): now})
                pipe.expire(key, self.window_seconds)
                
                res = await pipe.execute()
                count = res[1]

            if count > self.limit:
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. Please try again later."
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Redis rate limiter exception: {e}")
            return
