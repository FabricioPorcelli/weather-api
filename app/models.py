from pydantic import BaseModel, Field


class WeatherResponse(BaseModel):
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
