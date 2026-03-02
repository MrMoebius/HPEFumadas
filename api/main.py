"""
FastAPI — API REST del Gemelo Digital del Camión de Bomberos.
"""

import sys
import os
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from api.state import shared_state
from api.routes.twin import router as twin_router
from api.routes.alerts import router as alerts_router
from api.routes.simulation import router as simulation_router
from api.routes.predictions import router as predictions_router
from api.routes.ecosystem import router as ecosystem_router
from api.websocket import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicia la suscripción MQTT al arrancar la API."""
    shared_state.start()
    logger.info("API conectada a MQTT y lista")
    yield
    shared_state.stop()
    logger.info("API desconectada")


app = FastAPI(
    title="Gemelo Digital — Camión de Bomberos BOM-001",
    description="API REST para monitoreo, alertas, simulación y predicción del gemelo digital",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(twin_router, prefix="/api/v1/twin", tags=["Twin"])
app.include_router(alerts_router, prefix="/api/v1", tags=["Alertas"])
app.include_router(simulation_router, prefix="/api/v1/simulate", tags=["Simulación"])
app.include_router(predictions_router, prefix="/api/v1/predict", tags=["Predicción"])
app.include_router(ecosystem_router, prefix="/api/v1/ecosystem", tags=["Ecosistema"])
app.include_router(ws_router, prefix="/api/v1", tags=["WebSocket"])


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "bomberos-digital-twin-api",
        "vehicle_id": shared_state.vehicle_id,
        "mqtt_connected": shared_state.mqtt_connected,
    }


@app.get("/")
def root():
    return {
        "project": "Gemelo Digital — Camión de Bomberos",
        "vehicle_id": "BOM-001",
        "docs": "/docs",
        "health": "/health",
    }
