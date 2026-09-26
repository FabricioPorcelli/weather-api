# Imagen base: Python 3.13 liviano, misma versión menor que el entorno local.
FROM python:3.13-slim

WORKDIR /app

# Logs sin buffer (se ven al instante) y sin archivos .pyc dentro del contenedor.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Primero solo las dependencias: si no cambian, Docker reutiliza esta capa cacheada.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código de la aplicación. Tests y archivos locales quedan afuera por .dockerignore.
COPY app ./app

EXPOSE 8000

# 0.0.0.0 es obligatorio: dentro del contenedor, 127.0.0.1 no es accesible desde afuera.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
