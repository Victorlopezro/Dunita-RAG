FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Instalar Playwright para Crawl4AI
RUN pip install --no-cache-dir playwright && \
    playwright install chromium && \
    playwright install-deps chromium

WORKDIR /app

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY api/ ./api/
COPY ingest/ ./ingest/

# Crear directorios de datos
RUN mkdir -p /app/data/raw /app/data/parsed /app/data/chunks /app/data/eval

# Variables de entorno por defecto
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
