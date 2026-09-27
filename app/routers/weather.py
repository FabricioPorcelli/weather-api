"""Capa HTTP del recurso clima (v1).

Recibe el request, delega en el service y solo se ocupa del header X-Cache:
la traducción de excepciones de dominio a códigos HTTP vive en app/errors.py.
"""

from typing import Annotated

from fastapi import APIRouter, Path, Query, Request, Response

from app.limiter import RATE_LIMIT, limiter
from app.models import ForecastResponse, WeatherResponse
from app.services import weather as weather_service

router = APIRouter(prefix="/v1", tags=["weather"])

City = Annotated[
    str,
    Path(
        min_length=2,
        max_length=100,
        description="Nombre de la ciudad, por ejemplo Madrid",
    ),
]
Latitude = Annotated[
    float, Path(ge=-90, le=90, description="Latitud en grados decimales")
]
Longitude = Annotated[
    float, Path(ge=-180, le=180, description="Longitud en grados decimales")
]
Days = Annotated[int, Query(ge=1, le=15, description="Cantidad de días de pronóstico")]


def _cache_header(response: Response, from_cache: bool) -> None:
    response.headers["X-Cache"] = "HIT" if from_cache else "MISS"


@router.get("/weather/{city}")
@limiter.limit(RATE_LIMIT)  # Debe ir debajo de @router.get.
async def get_current_by_city(
    request: Request,  # Requerido por slowapi para identificar al cliente.
    response: Response,
    city: City,
) -> WeatherResponse:
    """Devuelve el clima actual de una ciudad."""
    weather, from_cache = await weather_service.get_current(city=city)
    _cache_header(response, from_cache)
    return weather


@router.get("/weather/coords/{lat}/{lon}")
@limiter.limit(RATE_LIMIT)
async def get_current_by_coords(
    request: Request,
    response: Response,
    lat: Latitude,
    lon: Longitude,
) -> WeatherResponse:
    """Devuelve el clima actual para un par de coordenadas."""
    weather, from_cache = await weather_service.get_current(lat=lat, lon=lon)
    _cache_header(response, from_cache)
    return weather


@router.get("/forecast/{city}")
@limiter.limit(RATE_LIMIT)
async def get_forecast_by_city(
    request: Request,
    response: Response,
    city: City,
    days: Days = 5,
) -> ForecastResponse:
    """Devuelve el pronóstico diario de una ciudad."""
    forecast, from_cache = await weather_service.get_forecast(days, city=city)
    _cache_header(response, from_cache)
    return forecast


@router.get("/forecast/coords/{lat}/{lon}")
@limiter.limit(RATE_LIMIT)
async def get_forecast_by_coords(
    request: Request,
    response: Response,
    lat: Latitude,
    lon: Longitude,
    days: Days = 5,
) -> ForecastResponse:
    """Devuelve el pronóstico diario para un par de coordenadas."""
    forecast, from_cache = await weather_service.get_forecast(days, lat=lat, lon=lon)
    _cache_header(response, from_cache)
    return forecast
