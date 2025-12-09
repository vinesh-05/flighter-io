import os
import redis.asyncio as redis

redis_client = redis.from_url(
    os.getenv("REDIS_URL"),
    encoding="utf-8",
    decode_responses=True
)
