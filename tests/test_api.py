"""Tests de integración del endpoint GET /weather/{city}.

Se ejecuta la app completa (router + service + caché) con el proveedor externo
mockeado: se verifica el contrato de respuesta y la traducción de errores a
códigos HTTP.
"""

from datetime import datetime, timezone

import httpx
from redis.exceptions import RedisError

from app.services import cache

UPSTREAM_PATH = "/VisualCrossingWebServices/rest/services/timeline/Madrid"

UPSTREAM_PAYLOAD = {
    "resolvedAddress": "Madrid, Spain",
    "currentConditions": {
        "temp": 21.5,
        "feelslike": 20.3,
        "humidity": 55.4,
        "conditions": "Parcialmente nublado",
        "windspeed": 12.4,
        "precip": 0.0,
        "datetimeEpoch": 1789900000,
    },
}


class BrokenRedis:
    """Cliente que simula un Redis caído."""

    async def get(self, key):
        raise RedisError("conexión rechazada")

    async def set(self, key, value, ex=None):
        raise RedisError("conexión rechazada")


def test_get_weather_ok(client, mock_weather_api):
    mock_weather_api.get(UPSTREAM_PATH).mock(
        return_value=httpx.Response(200, json=UPSTREAM_PAYLOAD)
    )

    response = client.get("/weather/Madrid")

    assert response.status_code == 200
    assert response.headers["X-Cache"] == "MISS"
    body = response.json()
    assert body["location"] == "Madrid, Spain"
    assert body["temperature_c"] == 21.5
    assert body["humidity"] == 55
    assert body["conditions"] == "Parcialmente nublado"
    assert body["updated_at"] == datetime.fromtimestamp(
        1789900000, tz=timezone.utc
    ).isoformat()


def test_second_request_comes_from_cache(client, mock_weather_api):
    route = mock_weather_api.get(UPSTREAM_PATH).mock(
        return_value=httpx.Response(200, json=UPSTREAM_PAYLOAD)
    )

    first = client.get("/weather/Madrid")
    second = client.get("/weather/madrid")

    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"
    assert route.call_count == 1


def test_unknown_city_returns_404(client, mock_weather_api):
    mock_weather_api.get(UPSTREAM_PATH).mock(
        return_value=httpx.Response(400, json={"message": "No such location"})
    )

    response = client.get("/weather/Madrid")

    assert response.status_code == 404


def test_upstream_timeout_returns_504(client, mock_weather_api):
    mock_weather_api.get(UPSTREAM_PATH).mock(
        side_effect=httpx.TimeoutException("timeout")
    )

    response = client.get("/weather/Madrid")

    assert response.status_code == 504


def test_upstream_error_returns_502(client, mock_weather_api):
    mock_weather_api.get(UPSTREAM_PATH).mock(
        return_value=httpx.Response(500, text="server error")
    )

    response = client.get("/weather/Madrid")

    assert response.status_code == 502


def test_too_short_city_returns_422(client):
    response = client.get("/weather/a")

    assert response.status_code == 422


def test_works_when_redis_is_down(client, mock_weather_api, monkeypatch):
    monkeypatch.setattr(cache, "get_redis", lambda: BrokenRedis())
    mock_weather_api.get(UPSTREAM_PATH).mock(
        return_value=httpx.Response(200, json=UPSTREAM_PAYLOAD)
    )

    response = client.get("/weather/Madrid")

    assert response.status_code == 200
    assert response.headers["X-Cache"] == "MISS"
