import json
import logging
from functools import lru_cache

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True)


async def get_json(key: str) -> dict | None:
    try:
        raw = await get_redis().get(key)
    except RedisError as exc:
        logger.warning("Redis no disponible al leer %s: %s", key, exc)
        return None

    if raw is None:
        return None
    return json.loads(raw)


async def set_json(key: str, value: dict, ttl_seconds: int) -> None:
    try:
        await get_redis().set(
            key, json.dumps(value, ensure_ascii=False), ex=ttl_seconds
        )
    except RedisError as exc:
        logger.warning("Redis no disponible al escribir %s: %s", key, exc)
