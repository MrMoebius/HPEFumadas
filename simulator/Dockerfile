FROM python:3.11-slim

WORKDIR /app

COPY simulator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config/ ./config/
COPY simulator/ ./simulator/

CMD ["python", "-m", "simulator.vehicle_simulator"]
