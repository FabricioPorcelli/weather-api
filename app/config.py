"""Configuración tipada de la aplicación, cargada desde variables de entorno.

Cada campo se puede pisar desde el archivo .env o desde el entorno del sistema
(en pydantic-settings los nombres no distinguen mayúsculas: WEATHER_API_KEY
alimenta el campo weather_api_key).
"""

from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Valores de configuración del servicio."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Obligatoria: si falta, la app falla al arrancar con un error explícito.
    weather_api_key: str

    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 43200  # 12 horas para el clima actual
    forecast_cache_ttl_seconds: int = 3600  # 1 hora para el pronóstico
    weather_api_base_url: str = (
        "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"
    )
    upstream_timeout_seconds: float = 10.0
    rate_limit: str = "10/minute"
    # Orígenes web permitidos para CORS. Vacío = sin CORS, que es lo seguro por defecto.
    # NoDecode evita que pydantic-settings intente parsear el string como JSON
    # antes de que corra el validador que separa por comas.
    cors_origins: Annotated[list[str], NoDecode] = []

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value):
        """Acepta un string separado por comas (formato cómodo para .env)."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración una sola vez (singleton).

    Al quedar cacheada, los cambios en .env requieren reiniciar el proceso.
    """
    return Settings()
