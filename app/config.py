"""Configuración tipada de la aplicación, cargada desde variables de entorno.

Cada campo se puede pisar desde el archivo .env o desde el entorno del sistema
(en pydantic-settings los nombres no distinguen mayúsculas: WEATHER_API_KEY
alimenta el campo weather_api_key).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Valores de configuración del servicio."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Obligatoria: si falta, la app falla al arrancar con un error explícito.
    weather_api_key: str

    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 43200  # 12 horas
    weather_api_base_url: str = (
        "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"
    )
    upstream_timeout_seconds: float = 10.0
    rate_limit: str = "10/minute"


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración una sola vez (singleton).

    Al quedar cacheada, los cambios en .env requieren reiniciar el proceso.
    """
    return Settings()
