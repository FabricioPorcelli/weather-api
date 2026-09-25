"""Configuración del rate limiting con slowapi.

Los contadores se guardan en Redis para compartirlos entre procesos. Si Redis
no responde, slowapi cae a un almacenamiento en memoria: el límite sigue
aplicándose (por proceso) y la API no se cae.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,  # Limita por IP del cliente.
    storage_uri=settings.redis_url,
    headers_enabled=True,  # Agrega los headers X-RateLimit-* a las respuestas.
    in_memory_fallback_enabled=True,
)

# Formato de la librería limits: "10/minute", "100/hour", "5/second", etc.
RATE_LIMIT = settings.rate_limit
