"""Contrato público de la API: define la forma exacta del JSON de respuesta.

Pydantic valida los datos al construir el objeto, los serializa a JSON y
documenta el esquema automáticamente en /docs. Los clientes dependen de este
contrato, no del esquema del proveedor externo.
"""

from pydantic import BaseModel, Field


class WeatherResponse(BaseModel):
    """Clima actual de una ciudad, ya normalizado."""

    location: str = Field(description="Ciudad resuelta por el proveedor")
    temperature_c: float = Field(description="Temperatura actual en grados Celsius")
    feels_like_c: float = Field(description="Sensación térmica en grados Celsius")
    humidity: int = Field(ge=0, le=100, description="Humedad relativa en porcentaje")
    conditions: str = Field(description="Descripción textual del estado del cielo")
    wind_speed_kmh: float = Field(ge=0, description="Velocidad del viento en km/h")
    precipitation_mm: float = Field(
        default=0.0, ge=0, description="Precipitación acumulada en milímetros"
    )
    updated_at: str = Field(description="Momento de la última actualización de los datos")
