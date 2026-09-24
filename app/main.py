from typing import Annotated

from fastapi import FastAPI, Path

from app.models import WeatherResponse

app = FastAPI(
    title="Weather API Wrapper",
    description="API que devuelve el clima de una ciudad usando Visual Crossing.",
    version="0.1.0",
)


@app.get("/weather/{city}")
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
    return WeatherResponse(
        location=city.title(),
        temperature_c=21.5,
        feels_like_c=20.3,
        humidity=55,
        conditions="Parcialmente nublado",
        wind_speed_kmh=12.4,
        updated_at="2026-09-24T12:00:00",
    )
