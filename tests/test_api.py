"""Tests de integración de los endpoints v1 de clima y pronóstico.

Se ejecuta la app completa (router + service + caché) con el proveedor externo
mockeado: se verifica el contrato de respuesta, el header X-Cache y la
traducción de errores a códigos HTTP (app/errors.py).
"""

from datetime import date, datetime, timedelta, timezone

import httpx
from redis.exceptions import RedisError

from app.services import cache

CITY_PATH = "/VisualCrossingWebServices/rest/services/timeline/Madrid"
COORDS_PATH = "/VisualCrossingWebServices/rest/services/timeline/40.42,-3.70"

CURRENT_PAYLOAD = {
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


def _forecast_day(index: int) -> dict:
    return {
        "datetime": f"2026-09-{20 + index:02d}",
        "tempmax": 25.0 + index,
        "tempmin": 12.0 + index,
        "temp": 18.0 + index,
        "precip": 0.0,
        "precipprob": 10 + index,
        "conditions": "Parcialmente nublado",
        "windspeed": 9.0 + index,
        "sunrise": "07:10:00",
        "sunset": "19:40:00",
    }


FORECAST_PAYLOAD = {
    "resolvedAddress": "Madrid, Spain",
    "days": [_forecast_day(index) for index in range(7)],
}

HISTORY_PATH = f"{CITY_PATH}/2024-10-01/2024-10-03"
COORDS_HISTORY_PATH = f"{COORDS_PATH}/2024-10-01/2024-10-03"


def _historical_day(index: int) -> dict:
    return {
        "datetime": f"2024-10-{1 + index:02d}",
        "tempmax": 20.0 + index,
        "tempmin": 10.0 + index,
        "temp": 15.0 + index,
        "precip": 0.0,
        "precipprob": None,
        "conditions": "Despejado",
        "windspeed": 8.0 + index,
        "sunrise": "07:20:00",
        "sunset": "18:50:00",
    }


HISTORICAL_PAYLOAD = {
    "resolvedAddress": "Madrid, Spain",
    "days": [_historical_day(index) for index in range(3)],
}


class BrokenRedis:
    """Cliente que simula un Redis caído."""

    async def get(self, key):
        raise RedisError("conexión rechazada")

    async def set(self, key, value, ex=None):
        raise RedisError("conexión rechazada")


def test_get_current_by_city_ok(client, mock_weather_api):
    mock_weather_api.get(CITY_PATH).mock(
        return_value=httpx.Response(200, json=CURRENT_PAYLOAD)
    )

    response = client.get("/v1/weather/Madrid")

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
    route = mock_weather_api.get(CITY_PATH).mock(
        return_value=httpx.Response(200, json=CURRENT_PAYLOAD)
    )

    first = client.get("/v1/weather/Madrid")
    second = client.get("/v1/weather/madrid")

    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"
    assert route.call_count == 1


def test_current_by_coords_rounds_cache_key(client, mock_weather_api):
    route = mock_weather_api.get(COORDS_PATH).mock(
        return_value=httpx.Response(200, json=CURRENT_PAYLOAD)
    )

    first = client.get("/v1/weather/coords/40.42/-3.70")
    second = client.get("/v1/weather/coords/40.421/-3.699")

    assert first.status_code == 200
    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"
    assert route.call_count == 1


def test_invalid_latitude_returns_422(client):
    response = client.get("/v1/weather/coords/100/10")

    assert response.status_code == 422


def test_forecast_by_city_ok(client, mock_weather_api):
    mock_weather_api.get(CITY_PATH).mock(
        return_value=httpx.Response(200, json=FORECAST_PAYLOAD)
    )

    response = client.get("/v1/forecast/Madrid?days=5")

    assert response.status_code == 200
    assert response.headers["X-Cache"] == "MISS"
    body = response.json()
    assert body["location"] == "Madrid, Spain"
    assert len(body["days"]) == 5
    first_day = body["days"][0]
    assert first_day["date"] == "2026-09-20"
    assert first_day["temp_max_c"] == 25.0
    assert first_day["precipitation_probability"] == 10
    assert first_day["sunrise"] == "07:10:00"


def test_forecast_by_coords_ok(client, mock_weather_api):
    mock_weather_api.get(COORDS_PATH).mock(
        return_value=httpx.Response(200, json=FORECAST_PAYLOAD)
    )

    response = client.get("/v1/forecast/coords/40.42/-3.70?days=3")

    assert response.status_code == 200
    assert len(response.json()["days"]) == 3


def test_forecast_days_out_of_range_returns_422(client):
    response = client.get("/v1/forecast/Madrid?days=99")

    assert response.status_code == 422


async def test_forecast_cache_ttl(client, fake_redis, mock_weather_api):
    mock_weather_api.get(CITY_PATH).mock(
        return_value=httpx.Response(200, json=FORECAST_PAYLOAD)
    )

    client.get("/v1/forecast/Madrid?days=5")

    ttl = await fake_redis.ttl("forecast:madrid:5")
    assert 0 < ttl <= 3600


def test_unknown_city_returns_404(client, mock_weather_api):
    mock_weather_api.get(CITY_PATH).mock(
        return_value=httpx.Response(400, json={"message": "No such location"})
    )

    response = client.get("/v1/weather/Madrid")

    assert response.status_code == 404


def test_upstream_timeout_returns_504(client, mock_weather_api):
    mock_weather_api.get(CITY_PATH).mock(
        side_effect=httpx.TimeoutException("timeout")
    )

    response = client.get("/v1/weather/Madrid")

    assert response.status_code == 504


def test_upstream_error_returns_502(client, mock_weather_api):
    mock_weather_api.get(CITY_PATH).mock(
        return_value=httpx.Response(500, text="server error")
    )

    response = client.get("/v1/weather/Madrid")

    assert response.status_code == 502


def test_too_short_city_returns_422(client):
    response = client.get("/v1/weather/a")

    assert response.status_code == 422


def test_works_when_redis_is_down(client, mock_weather_api, monkeypatch):
    monkeypatch.setattr(cache, "get_redis", lambda: BrokenRedis())
    mock_weather_api.get(CITY_PATH).mock(
        return_value=httpx.Response(200, json=CURRENT_PAYLOAD)
    )

    response = client.get("/v1/weather/Madrid")

    assert response.status_code == 200
    assert response.headers["X-Cache"] == "MISS"


def test_history_by_city_ok_and_cached(client, mock_weather_api):
    route = mock_weather_api.get(HISTORY_PATH).mock(
        return_value=httpx.Response(200, json=HISTORICAL_PAYLOAD)
    )

    first = client.get("/v1/history/Madrid?start=2024-10-01&end=2024-10-03")
    second = client.get("/v1/history/Madrid?start=2024-10-01&end=2024-10-03")

    assert first.status_code == 200
    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"
    assert route.call_count == 1
    body = first.json()
    assert body["location"] == "Madrid, Spain"
    assert len(body["days"]) == 3
    assert body["days"][0]["date"] == "2024-10-01"
    assert body["days"][0]["precipitation_probability"] is None


def test_history_by_coords_ok(client, mock_weather_api):
    mock_weather_api.get(COORDS_HISTORY_PATH).mock(
        return_value=httpx.Response(200, json=HISTORICAL_PAYLOAD)
    )

    response = client.get(
        "/v1/history/coords/40.42/-3.70?start=2024-10-01&end=2024-10-03"
    )

    assert response.status_code == 200
    assert len(response.json()["days"]) == 3


async def test_history_ttl_is_long_for_past_ranges(client, fake_redis, mock_weather_api):
    mock_weather_api.get(HISTORY_PATH).mock(
        return_value=httpx.Response(200, json=HISTORICAL_PAYLOAD)
    )

    client.get("/v1/history/Madrid?start=2024-10-01&end=2024-10-03")

    ttl = await fake_redis.ttl("history:madrid:2024-10-01:2024-10-03")
    assert ttl > 3600


async def test_history_ttl_is_short_when_range_includes_today(
    client, fake_redis, mock_weather_api
):
    today = date.today()
    start = today - timedelta(days=2)
    path = f"{CITY_PATH}/{start.isoformat()}/{today.isoformat()}"
    key = f"history:madrid:{start.isoformat()}:{today.isoformat()}"
    mock_weather_api.get(path).mock(
        return_value=httpx.Response(200, json=HISTORICAL_PAYLOAD)
    )

    response = client.get(
        f"/v1/history/Madrid?start={start.isoformat()}&end={today.isoformat()}"
    )

    assert response.status_code == 200
    ttl = await fake_redis.ttl(key)
    assert 0 < ttl <= 3600


def test_history_start_after_end_returns_422(client):
    response = client.get("/v1/history/Madrid?start=2024-10-10&end=2024-10-01")

    assert response.status_code == 422


def test_history_future_end_returns_422(client):
    response = client.get("/v1/history/Madrid?start=2024-10-01&end=2030-01-01")

    assert response.status_code == 422


def test_history_range_too_long_returns_422(client):
    response = client.get("/v1/history/Madrid?start=2020-01-01&end=2024-01-01")

    assert response.status_code == 422


def test_history_invalid_date_returns_422(client):
    response = client.get("/v1/history/Madrid?start=2024-13-01&end=2024-12-01")

    assert response.status_code == 422


def test_history_missing_dates_returns_422(client):
    response = client.get("/v1/history/Madrid")

    assert response.status_code == 422
