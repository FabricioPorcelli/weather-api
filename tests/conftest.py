"""Fixtures compartidas por los tests.

Los tests no tocan la red ni dependen de Redis real: el proveedor externo se
mockea con respx y la caché con fakeredis. Además el rate limiting se
desactiva, porque su estado (ventanas de tiempo por IP) haría los tests
dependientes de cuándo se ejecutan.
"""

import os

# Variables de prueba antes de importar la app, para no depender del .env real.
os.environ["WEATHER_API_KEY"] = "test-key"

import fakeredis.aioredis
import pytest
import respx
from fastapi.testclient import TestClient

from app.limiter import limiter
from app.main import app
from app.services import cache


@pytest.fixture(autouse=True)
def _disable_rate_limit():
    """Desactiva el limiter durante los tests y lo restaura al terminar."""
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    """Reemplaza el cliente Redis real por uno en memoria (aislado por test)."""
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(cache, "get_redis", lambda: client)
    return client


@pytest.fixture
def client() -> TestClient:
    """Cliente HTTP que ejecuta la app FastAPI en el mismo proceso."""
    return TestClient(app)


@pytest.fixture
def mock_weather_api():
    """Intercepta las llamadas httpx a Visual Crossing y falla si hay otras."""
    with respx.mock(base_url="https://weather.visualcrossing.com") as mock:
        yield mock
