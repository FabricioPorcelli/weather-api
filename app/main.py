"""Punto de entrada de la aplicación.

Crea la instancia de FastAPI, registra el rate limiter, los handlers de
errores, el CORS opcional y monta los routers.
Se ejecuta con: uvicorn app.main:app
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.errors import register_exception_handlers
from app.limiter import limiter
from app.routers.weather import router as weather_router

app = FastAPI(
    title="Weather API Wrapper",
    description=(
        "API que devuelve el clima actual y el pronóstico de una ciudad o de "
        "un par de coordenadas, usando Visual Crossing como proveedor."
    ),
    version="1.0.0",
)

# slowapi busca el limiter en app.state y usa este handler para responder 429.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

register_exception_handlers(app)


@app.get("/health")
async def health() -> dict[str, str]:
    """Indica que la aplicación está viva, sin consultar servicios externos."""
    return {"status": "ok"}


# CORS solo si hay orígenes configurados; expone X-Cache para clientes web.
settings = get_settings()
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET"],
        allow_headers=["*"],
        expose_headers=["X-Cache"],
    )

app.include_router(weather_router)
