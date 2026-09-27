# Weather API Wrapper

API REST en Python que consulta el clima actual y el pronóstico de una ciudad o de
un par de coordenadas a [Visual Crossing](https://www.visualcrossing.com/weather-api),
normaliza la respuesta a un contrato propio y la sirve con caché en Redis.

> Proyecto en construcción, desarrollado por fases a partir de
> [este proyecto de roadmap.sh](https://roadmap.sh/projects/weather-api-wrapper-service).

## Estado

- [x] API v1: clima actual y pronóstico (por ciudad o coordenadas)
- [x] Validación con Pydantic y documentación automática en `/docs`
- [x] Integración con Visual Crossing (`httpx`) con manejo de errores y timeouts
- [x] Caché con Redis y TTL por tipo de dato (12 h actual / 1 h pronóstico)
- [x] Rate limiting por IP con slowapi (Redis + fallback en memoria)
- [x] 17 tests sin red ni Redis reales (respx + fakeredis)
- [x] Docker Compose: API + Redis con un solo comando
- [ ] Autenticación por API key y deploy (futuro)

## Stack

Python 3.13 · FastAPI · Uvicorn · Pydantic · httpx · Redis · slowapi · pytest · Docker

## Endpoints (v1)

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/v1/weather/{city}` | Clima actual por ciudad |
| GET | `/v1/weather/coords/{lat}/{lon}` | Clima actual por coordenadas |
| GET | `/v1/forecast/{city}?days=5` | Pronóstico diario (1 a 15 días) |
| GET | `/v1/forecast/coords/{lat}/{lon}?days=5` | Pronóstico por coordenadas |

```bash
curl -i "http://localhost:8000/v1/weather/Madrid"
curl -i "http://localhost:8000/v1/weather/coords/-34.60/-58.38"
curl -i "http://localhost:8000/v1/forecast/Madrid?days=5"
```

Clima actual:

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

Pronóstico:

```json
{
  "location": "Madrid, Spain",
  "days": [
    {
      "date": "2026-09-25",
      "temp_max_c": 25.0,
      "temp_min_c": 14.2,
      "temp_c": 19.6,
      "precipitation_mm": 0.0,
      "precipitation_probability": 10,
      "conditions": "Parcialmente nublado",
      "wind_speed_kmh": 12.0,
      "sunrise": "08:05:00",
      "sunset": "20:05:00"
    }
  ]
}
```

Todas las respuestas incluyen `X-Cache: HIT | MISS` para saber si se resolvieron desde Redis.

Errores: `404` ubicación no encontrada, `422` parámetros inválidos, `429` rate limit,
`502` proveedor no disponible, `504` timeout del proveedor.

Documentación interactiva en `http://localhost:8000/docs`.

## Cómo correrlo

Requisitos: Python 3.13, Docker y una API key gratuita de Visual Crossing.

**Todo con Docker (recomendado):**

```bash
cp .env.example .env            # completar WEATHER_API_KEY
docker compose up -d --build    # API + Redis
# http://localhost:8000/docs
```

**Modo desarrollo (API local, Redis en Docker):**

```bash
conda create -n weather-api python=3.13 -y
conda activate weather-api
python -m pip install -r requirements.txt

cp .env.example .env
docker compose up -d redis
uvicorn app.main:app --reload
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
├── main.py               # app FastAPI: limiter, errores, CORS y routers
├── config.py             # configuración tipada desde variables de entorno
├── models.py             # contratos públicos (Pydantic)
├── errors.py             # excepciones de dominio -> códigos HTTP
├── limiter.py            # rate limiting (slowapi)
├── routers/weather.py    # capa HTTP v1
└── services/
    ├── weather.py        # caché + llamada a Visual Crossing + mapeo
    └── cache.py          # wrapper de Redis (get/set con TTL)
```

## Pensada para otros proyectos

La API está pensada para que otros proyectos la consuman por HTTP, sin integrar
Visual Crossing por su cuenta:

- Cualquier aplicación (web, móvil, bot o servicio backend) obtiene clima y pronóstico
  con un simple `GET`, contra un contrato estable y versionado.
- La API key del proveedor, la caché y el rate limiting quedan centralizados acá,
  no duplicados en cada proyecto.
- Si el consumidor corre en otro origen desde un navegador, se habilita CORS con la
  variable `CORS_ORIGINS` del `.env`.

## Por qué este proyecto

- Consume una API de terceros sin filtrar su esquema: los clientes dependen de un
  contrato propio y estable, versionado en `/v1`.
- Aplica caché con TTL (patrón cache-aside) y se degrada con gracia si Redis no responde.
- Configura secretos por variables de entorno y maneja errores con códigos HTTP correctos.
- Está preparado para ser reutilizado y hosteado como servicio para otros proyectos.
