from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    weather_api_key: str
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 43200
    weather_api_base_url: str = (
        "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"
    )
    upstream_timeout_seconds: float = 10.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
