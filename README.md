# Weather API Wrapper

API REST que consulta el clima actual de una ciudad a [Visual Crossing](https://www.visualcrossing.com/weather-api),
normaliza la respuesta a un contrato propio y la sirve con caché en Redis para evitar llamadas repetidas al proveedor.

> Proyecto en construcción, desarrollado por fases a partir de > [este proyecto de roadmap.sh](https://roadmap.sh/projects/weather-api-wrapper-service).

## Estado

- [x] API base con FastAPI, validación con Pydantic y documentación automática
- [x] Integración con Visual Crossing (`httpx`) con manejo de errores y timeouts
- [x] Caché con Redis con TTL y degradación si Redis no está disponible
- [x] Rate limiting por IP con slowapi (Redis + fallback en memoria)
- [x] Tests automatizados (11 tests, sin red ni Redis reales)
- [ ] Dockerfile de la aplicación

## Stack

Python 3.13 · FastAPI · Uvicorn · Pydantic · httpx · Redis (Docker) · slowapi · pytest

## Endpoint

### `GET /weather/{city}`

```bash
curl -i http://localhost:8000/weather/Madrid
```

```json
{
  "location": "Madrid, Spain",
  "temperature_c": 21.5,
  "feels_like_c": 20.3,
  "humidity": 55,
  "conditions": "Parcialmente nublado",
  "wind_speed_kmh": 12.4,
  "precipitation_mm": 0.0,
  "updated_at": "2026-09-25T12:00:00+00:00"
}
```

La respuesta incluye el header `X-Cache: HIT | MISS` para saber si se resolvió desde Redis.

Errores documentados: `404` ciudad no encontrada, `422` nombre de ciudad inválido, `502` proveedor no disponible, `504` timeout del proveedor.

Documentación interactiva en `http://localhost:8000/docs`.

## Cómo correrlo localmente

Requisitos: Python 3.13, Docker y una API key gratuita de Visual Crossing.

```bash
conda create -n weather-api python=3.13 -y
conda activate weather-api
python -m pip install -r requirements.txt

cp .env.example .env          # completar WEATHER_API_KEY
docker compose up -d          # levanta Redis
uvicorn app.main:app --reload # http://localhost:8000/docs
```

## Tests

```bash
python -m pip install -r requirements-dev.txt
pytest -v
```

Los tests usan `respx` (mock del proveedor), `fakeredis` (caché en memoria) y
`TestClient`: corren sin red y sin Docker.

## Estructura

```
app/
├── main.py               # crea la app FastAPI y monta los routers
├── config.py             # configuración tipada desde variables de entorno
├── models.py             # contrato público (Pydantic)
├── routers/weather.py    # capa HTTP: traduce errores de dominio a status codes
└── services/
    ├── weather.py        # lógica: caché + llamada a Visual Crossing + mapeo
    └── cache.py          # wrapper de Redis (get/set con TTL)
```

## Por qué este proyecto

- Consume una API de terceros sin filtrar su esquema: los clientes dependen de un contrato propio y estable.
- Aplica caché con TTL (patrón cache-aside) y se degrada con gracia si Redis no responde.
- Configura secretos por variables de entorno y maneja errores con códigos HTTP correctos.
- Está pensado para ser reutilizado: cualquier otro proyecto puede consumir esta API por HTTP en lugar de integrar Visual Crossing por su cuenta.
