from typing import Annotated

from fastapi import APIRouter, HTTPException, Path

from app.models import WeatherResponse
from app.services.weather import (
    CityNotFoundError,
    UpstreamError,
    UpstreamTimeoutError,
    fetch_weather,
)

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/{city}")
async def get_weather(
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
        return await fetch_weather(city)
    except CityNotFoundError:
        raise HTTPException(status_code=404, detail=f"No se encontró la ciudad: {city}")
    except UpstreamTimeoutError:
        raise HTTPException(
            status_code=504, detail="El proveedor del clima no respondió a tiempo"
        )
    except UpstreamError:
        raise HTTPException(
            status_code=502, detail="El proveedor del clima no está disponible"
        )
