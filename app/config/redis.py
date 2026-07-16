import redis.asyncio as aioredis

from app.config.settings import settings

redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

async def get_redis_client():
    return redis_client
