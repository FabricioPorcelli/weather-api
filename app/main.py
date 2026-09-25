from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.limiter import limiter
from app.routers.weather import router as weather_router

app = FastAPI(
    title="Weather API Wrapper",
    description="API que devuelve el clima de una ciudad usando Visual Crossing.",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(weather_router)
