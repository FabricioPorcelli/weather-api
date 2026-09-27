"""Lógica de negocio del recurso clima.

Orquesta la caché y el proveedor externo (Visual Crossing), y traduce la
respuesta del proveedor a los contratos propios (WeatherResponse y
ForecastResponse). No conoce FastAPI ni códigos HTTP: de eso se encargan los
routers y los exception handlers de app/errors.py.
"""

import logging
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from app.config import get_settings
from app.models import DailyForecast, ForecastResponse, WeatherResponse
from app.services.cache import get_json, set_json

logger = logging.getLogger(__name__)

CURRENT_CACHE_PREFIX = "weather"
FORECAST_CACHE_PREFIX = "forecast"


class CityNotFoundError(Exception):
    """El proveedor no reconoce la ubicación consultada."""


class UpstreamError(Exception):
    """El proveedor falló o devolvió una respuesta inesperada."""


class UpstreamTimeoutError(UpstreamError):
    """El proveedor no respondió dentro del timeout configurado."""


def _resolve_location(
    city: str | None, lat: float | None, lon: float | None
) -> str:
    """Arma el valor de 'location' que espera el proveedor.

    Las coordenadas se redondean a 2 decimales (~1 km): así consultas y claves
    de caché de puntos cercanos quedan consistentes.
    """
    if lat is not None and lon is not None:
        return f"{lat:.2f},{lon:.2f}"
    if city:
        return city.strip()
    raise ValueError("Se requiere una ciudad o un par de coordenadas")


def _cache_key(prefix: str, location: str) -> str:
    """Normaliza la ubicación para que 'Madrid' y 'madrid' compartan caché."""
    return f"{prefix}:{location.strip().lower()}"


async def _request_upstream(location: str, include: str) -> dict:
    """Consulta Visual Crossing y devuelve el JSON crudo.

    Raises:
        CityNotFoundError: el proveedor no reconoce la ubicación.
        UpstreamTimeoutError: se superó upstream_timeout_seconds.
        UpstreamError: error de red u otra respuesta no exitosa.
    """
    settings = get_settings()
    url = f"{settings.weather_api_base_url}/{quote(location, safe=',')}"
    params = {
        "key": settings.weather_api_key,
        "unitGroup": "metric",
        "lang": "es",
        "include": include,
    }

    try:
        async with httpx.AsyncClient(timeout=settings.upstream_timeout_seconds) as client:
            response = await client.get(url, params=params)
    # TimeoutException hereda de HTTPError: debe capturarse primero.
    except httpx.TimeoutException as exc:
        raise UpstreamTimeoutError(f"Timeout consultando el clima de {location}") from exc
    except httpx.HTTPError as exc:
        raise UpstreamError(f"Error de red consultando el clima de {location}") from exc

    if response.status_code == 400:
        raise CityNotFoundError(location)
    if response.status_code != 200:
        raise UpstreamError(
            f"Visual Crossing respondió {response.status_code} para {location}"
        )
    return response.json()


def _to_weather_response(data: dict, fallback_location: str) -> WeatherResponse:
    """Mapea 'currentConditions' del proveedor a nuestro contrato."""
    current = data.get("currentConditions")
    if not current:
        raise UpstreamError(
            f"Respuesta sin condiciones actuales para {fallback_location}"
        )

    return WeatherResponse(
        location=data.get("resolvedAddress", fallback_location),
        temperature_c=current["temp"],
        feels_like_c=current["feelslike"],
        # El proveedor devuelve decimales (56.4); nuestro contrato la define entera.
        humidity=round(current["humidity"]),
        conditions=current.get("conditions", ""),
        wind_speed_kmh=current["windspeed"],
        precipitation_mm=current.get("precip") or 0.0,
        # datetimeEpoch son segundos Unix; el contrato usa ISO 8601 en UTC.
        updated_at=datetime.fromtimestamp(
            current["datetimeEpoch"], tz=timezone.utc
        ).isoformat(),
    )


def _to_forecast_response(
    data: dict, fallback_location: str, days: int
) -> ForecastResponse:
    """Mapea la lista 'days' del proveedor y recorta a los días pedidos."""
    daily = data.get("days")
    if not daily:
        raise UpstreamError(
            f"Respuesta sin pronóstico diario para {fallback_location}"
        )

    return ForecastResponse(
        location=data.get("resolvedAddress", fallback_location),
        days=[
            DailyForecast(
                date=day["datetime"],
                temp_max_c=day["tempmax"],
                temp_min_c=day["tempmin"],
                temp_c=day["temp"],
                precipitation_mm=day.get("precip") or 0.0,
                precipitation_probability=round(day.get("precipprob") or 0),
                conditions=day.get("conditions", ""),
                wind_speed_kmh=day["windspeed"],
                sunrise=day.get("sunrise", ""),
                sunset=day.get("sunset", ""),
            )
            for day in daily[:days]
        ],
    )


async def get_current(
    city: str | None = None, lat: float | None = None, lon: float | None = None
) -> tuple[WeatherResponse, bool]:
    """Clima actual con patrón cache-aside (por ciudad o por coordenadas).

    Returns:
        Tupla (clima, from_cache). El booleano se usa para el header X-Cache.
    """
    settings = get_settings()
    location = _resolve_location(city, lat, lon)
    key = _cache_key(CURRENT_CACHE_PREFIX, location)

    cached = await get_json(key)
    if cached is not None:
        logger.info("Cache HIT %s", key)
        return WeatherResponse.model_validate(cached), True

    logger.info("Cache MISS %s", key)
    data = await _request_upstream(location, include="current")
    weather = _to_weather_response(data, location)
    await set_json(key, weather.model_dump(mode="json"), settings.cache_ttl_seconds)
    return weather, False


async def get_forecast(
    days: int,
    city: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
) -> tuple[ForecastResponse, bool]:
    """Pronóstico diario con patrón cache-aside (por ciudad o por coordenadas).

    La clave de caché incluye la cantidad de días, y el TTL es más corto que el
    del clima actual porque el pronóstico cambia más seguido.
    """
    settings = get_settings()
    location = _resolve_location(city, lat, lon)
    key = f"{_cache_key(FORECAST_CACHE_PREFIX, location)}:{days}"

    cached = await get_json(key)
    if cached is not None:
        logger.info("Cache HIT %s", key)
        return ForecastResponse.model_validate(cached), True

    logger.info("Cache MISS %s", key)
    data = await _request_upstream(location, include="days")
    forecast = _to_forecast_response(data, location, days)
    await set_json(
        key, forecast.model_dump(mode="json"), settings.forecast_cache_ttl_seconds
    )
    return forecast, False
