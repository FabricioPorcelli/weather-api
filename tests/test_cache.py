"""Tests unitarios del wrapper de caché, usando fakeredis (sin Docker)."""

from redis.exceptions import RedisError

from app.services import cache


class BrokenRedis:
    """Cliente que simula un Redis caído."""

    async def get(self, key):
        raise RedisError("conexión rechazada")

    async def set(self, key, value, ex=None):
        raise RedisError("conexión rechazada")


async def test_set_and_get_json_roundtrip(fake_redis):
    await cache.set_json("weather:test", {"temperature_c": 21.5}, ttl_seconds=60)

    assert await cache.get_json("weather:test") == {"temperature_c": 21.5}


async def test_missing_key_returns_none(fake_redis):
    assert await cache.get_json("weather:noexiste") is None


async def test_ttl_is_applied(fake_redis):
    await cache.set_json("weather:test", {"temperature_c": 21.5}, ttl_seconds=60)

    ttl = await fake_redis.ttl("weather:test")

    assert 0 < ttl <= 60


async def test_redis_errors_are_swallowed(monkeypatch):
    monkeypatch.setattr(cache, "get_redis", lambda: BrokenRedis())

    assert await cache.get_json("weather:test") is None
    await cache.set_json("weather:test", {"temperature_c": 21.5}, ttl_seconds=60)
