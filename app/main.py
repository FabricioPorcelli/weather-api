from fastapi import FastAPI

from app.routers.weather import router as weather_router

app = FastAPI(
    title="Weather API Wrapper",
    description="API que devuelve el clima de una ciudad usando Visual Crossing.",
    version="0.1.0",
)

app.include_router(weather_router)