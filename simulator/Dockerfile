FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libspatialindex-dev \
        gdal-bin \
        libgdal-dev && \
    rm -rf /var/lib/apt/lists/*

COPY simulator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config/ ./config/
COPY simulator/ ./simulator/
COPY geo/ ./geo/

RUN mkdir -p /app/geo/cache

CMD ["python", "-m", "simulator.vehicle_simulator"]
