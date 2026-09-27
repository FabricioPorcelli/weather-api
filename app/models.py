"""Contrato público de la API: define la forma exacta del JSON de respuesta.

Pydantic valida los datos al construir el objeto, los serializa a JSON y
documenta el esquema automáticamente en /docs. Los clientes dependen de este
contrato, no del esquema del proveedor externo.
"""

from pydantic import BaseModel, Field


class WeatherResponse(BaseModel):
    """Clima actual de una ciudad o punto, ya normalizado."""

    location: str = Field(description="Ciudad o punto resuelto por el proveedor")
    temperature_c: float = Field(description="Temperatura actual en grados Celsius")
    feels_like_c: float = Field(description="Sensación térmica en grados Celsius")
    humidity: int = Field(ge=0, le=100, description="Humedad relativa en porcentaje")
    conditions: str = Field(description="Descripción textual del estado del cielo")
    wind_speed_kmh: float = Field(ge=0, description="Velocidad del viento en km/h")
    precipitation_mm: float = Field(
        default=0.0, ge=0, description="Precipitación acumulada en milímetros"
    )
    updated_at: str = Field(description="Momento de la última actualización de los datos")


class DailyForecast(BaseModel):
    """Resumen de un día de pronóstico."""

    date: str = Field(description="Fecha del día (formato YYYY-MM-DD)")
    temp_max_c: float = Field(description="Temperatura máxima en grados Celsius")
    temp_min_c: float = Field(description="Temperatura mínima en grados Celsius")
    temp_c: float = Field(description="Temperatura media en grados Celsius")
    precipitation_mm: float = Field(
        default=0.0, ge=0, description="Precipitación prevista en milímetros"
    )
    precipitation_probability: int = Field(
        ge=0, le=100, description="Probabilidad de precipitación en porcentaje"
    )
    conditions: str = Field(description="Descripción textual del estado del cielo")
    wind_speed_kmh: float = Field(ge=0, description="Velocidad máxima del viento en km/h")
    sunrise: str = Field(description="Hora local del amanecer")
    sunset: str = Field(description="Hora local del atardecer")


class ForecastResponse(BaseModel):
    """Pronóstico diario de una ciudad o punto."""

    location: str = Field(description="Ciudad o punto resuelto por el proveedor")
    days: list[DailyForecast] = Field(
        description="Días de pronóstico, del más cercano al más lejano"
    )
