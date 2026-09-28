"""Traducción centralizada de excepciones de dominio a respuestas HTTP.

Los routers delegan la lógica y no atrapan excepciones: al registrar los
handlers una sola vez, cualquier ruta (presente o futura) responde igual.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.services import weather as weather_service


def _error_response(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


async def _city_not_found(
    request: Request, exc: weather_service.CityNotFoundError
) -> JSONResponse:
    return _error_response(404, f"No se encontró la ubicación: {exc}")


async def _upstream_timeout(
    request: Request, exc: weather_service.UpstreamTimeoutError
) -> JSONResponse:
    return _error_response(504, "El proveedor del clima no respondió a tiempo")


async def _invalid_date_range(
    request: Request, exc: weather_service.InvalidDateRangeError
) -> JSONResponse:
    return _error_response(422, str(exc))


async def _upstream_error(
    request: Request, exc: weather_service.UpstreamError
) -> JSONResponse:
    return _error_response(502, "El proveedor del clima no está disponible")


def register_exception_handlers(app: FastAPI) -> None:
    """Asocia cada excepción de dominio con su handler.

    Starlette resuelve el handler por la clase de la excepción y su jerarquía;
    registrar UpstreamError cubre también a sus subclases.
    """
    app.add_exception_handler(weather_service.CityNotFoundError, _city_not_found)
    app.add_exception_handler(weather_service.UpstreamTimeoutError, _upstream_timeout)
    app.add_exception_handler(weather_service.UpstreamError, _upstream_error)
    app.add_exception_handler(weather_service.InvalidDateRangeError, _invalid_date_range)
