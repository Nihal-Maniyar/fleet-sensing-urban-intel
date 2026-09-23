# Production Dockerfile for Fleet Sensing Urban Intelligence Backend & GIS Dashboard
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for GIS and PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose FastAPI backend and GIS dashboard port
EXPOSE 8000

# Set environment defaults
ENV PYTHONUNBUFFERED=1 \
    DATABASE_URL=postgresql+psycopg://postgres:postgres@postgis:5432/urban_intelligence \
    MQTT_HOST=mqtt \
    MQTT_PORT=1883

# Run FastAPI backend with Uvicorn
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
