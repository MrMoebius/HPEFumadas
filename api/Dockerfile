FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config/ ./config/
COPY core/ ./core/
COPY ai/ ./ai/
COPY simulator/scenario_engine.py ./simulator/scenario_engine.py
COPY simulator/__init__.py ./simulator/__init__.py
COPY api/ ./api/

RUN mkdir -p /app/data

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
