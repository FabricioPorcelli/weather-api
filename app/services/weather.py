from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from app.config import get_settings
from app.models import WeatherResponse


class CityNotFoundError(Exception):
    pass


class UpstreamError(Exception):
    pass


class UpstreamTimeoutError(UpstreamError):
    pass


async def fetch_weather(city: str) -> WeatherResponse:
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
        humidity=round(current["humidity"]),
        conditions=current.get("conditions", ""),
        wind_speed_kmh=current["windspeed"],
        precipitation_mm=current.get("precip") or 0.0,
        updated_at=datetime.fromtimestamp(
            current["datetimeEpoch"], tz=timezone.utc
        ).isoformat(),
    )
