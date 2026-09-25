"""Lógica de negocio del recurso clima.

Orquesta la caché y el proveedor externo (Visual Crossing), y traduce la
respuesta del proveedor a nuestro contrato (WeatherResponse). No conoce
FastAPI ni códigos HTTP: de eso se encarga la capa de routers.
"""

import logging
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from app.config import get_settings
from app.models import WeatherResponse
from app.services.cache import get_json, set_json

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "weather"


class CityNotFoundError(Exception):
    """El proveedor no reconoce la ciudad consultada."""


class UpstreamError(Exception):
    """El proveedor falló o devolvió una respuesta inesperada."""


class UpstreamTimeoutError(UpstreamError):
    """El proveedor no respondió dentro del timeout configurado."""


def _cache_key(city: str) -> str:
    """Normaliza la ciudad para que 'Madrid', 'madrid' y 'MADRID' compartan caché."""
    return f"{CACHE_KEY_PREFIX}:{city.strip().lower()}"


async def get_weather(city: str) -> tuple[WeatherResponse, bool]:
    """Devuelve el clima de una ciudad aplicando el patrón cache-aside.

    Busca primero en Redis; si no está, consulta al proveedor, guarda el
    resultado con TTL y lo devuelve.

    Returns:
        Tupla (clima, from_cache). El booleano indica si la respuesta salió de
        Redis y se usa para informar el header X-Cache.
    """
    settings = get_settings()
    key = _cache_key(city)

    cached = await get_json(key)
    if cached is not None:
        logger.info("Cache HIT %s", key)
        return WeatherResponse.model_validate(cached), True

    logger.info("Cache MISS %s", key)
    weather = await fetch_weather(city)
    await set_json(key, weather.model_dump(mode="json"), settings.cache_ttl_seconds)
    return weather, False


async def fetch_weather(city: str) -> WeatherResponse:
    """Consulta Visual Crossing y mapea su respuesta a WeatherResponse.

    Raises:
        CityNotFoundError: el proveedor no reconoce la ciudad.
        UpstreamTimeoutError: se superó upstream_timeout_seconds.
        UpstreamError: error de red u otra respuesta no exitosa.
    """
    settings = get_settings()
    url = f"{settings.weather_api_base_url}/{quote(city)}"
    params = {
        "key": settings.weather_api_key,
        "unitGroup": "metric",
        "lang": "es",
        "include": "current",
    }

    try:
        async with httpx.AsyncClient(timeout=settings.upstream_timeout_seconds) as client:
            response = await client.get(url, params=params)
    # TimeoutException hereda de HTTPError: debe capturarse primero.
    except httpx.TimeoutException as exc:
        raise UpstreamTimeoutError(f"Timeout consultando el clima de {city}") from exc
    except httpx.HTTPError as exc:
        raise UpstreamError(f"Error de red consultando el clima de {city}") from exc

    if response.status_code == 400:
        raise CityNotFoundError(city)
    if response.status_code != 200:
        raise UpstreamError(
            f"Visual Crossing respondió {response.status_code} para {city}"
        )

    data = response.json()
    current = data.get("currentConditions")
    if not current:
        raise UpstreamError(f"Respuesta sin condiciones actuales para {city}")

    return WeatherResponse(
        location=data.get("resolvedAddress", city.title()),
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
