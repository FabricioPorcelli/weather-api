"""Acceso a Redis usado como caché de respuestas del proveedor.

Diseño best-effort: si Redis no está disponible, estas funciones registran un
warning y continúan. La caché es una optimización, no una dependencia.
"""

import json
import logging
from functools import lru_cache

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_redis() -> Redis:
    """Devuelve un cliente Redis único, reutilizando su pool de conexiones.

    decode_responses=True hace que GET devuelva str en lugar de bytes.
    """
    return Redis.from_url(get_settings().redis_url, decode_responses=True)


async def get_json(key: str) -> dict | None:
    """Lee una clave y deserializa su contenido JSON.

    Returns:
        El dict guardado, o None si la clave no existe o si Redis falla.
    """
    try:
        raw = await get_redis().get(key)
    except RedisError as exc:
        logger.warning("Redis no disponible al leer %s: %s", key, exc)
        return None

    if raw is None:
        return None
    return json.loads(raw)


async def set_json(key: str, value: dict, ttl_seconds: int) -> None:
    """Guarda un dict como JSON con expiración.

    El parámetro ex equivale al flag EX de Redis: la clave se elimina sola
    cuando vence el TTL. ensure_ascii=False conserva los acentos legibles.
    """
    try:
        await get_redis().set(
            key, json.dumps(value, ensure_ascii=False), ex=ttl_seconds
        )
    except RedisError as exc:
        logger.warning("Redis no disponible al escribir %s: %s", key, exc)
