from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Request, Response

from app.limiter import RATE_LIMIT, limiter
from app.models import WeatherResponse
from app.services import weather as weather_service

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/{city}")
@limiter.limit(RATE_LIMIT)
async def get_weather(
    request: Request,
    response: Response,
    city: Annotated[
        str,
        Path(
            min_length=2,
            max_length=100,
            description="Nombre de la ciudad, por ejemplo Madrid",
        ),
    ],
) -> WeatherResponse:
    try:
        weather, from_cache = await weather_service.get_weather(city)
    except weather_service.CityNotFoundError:
        raise HTTPException(status_code=404, detail=f"No se encontró la ciudad: {city}")
    except weather_service.UpstreamTimeoutError:
        raise HTTPException(
            status_code=504, detail="El proveedor del clima no respondió a tiempo"
        )
    except weather_service.UpstreamError:
        raise HTTPException(
            status_code=502, detail="El proveedor del clima no está disponible"
        )

    response.headers["X-Cache"] = "HIT" if from_cache else "MISS"
    return weather
