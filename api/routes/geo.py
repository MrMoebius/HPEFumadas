"""Endpoints REST para cartografía, rutas activas, POIs, tráfico y control."""

import json
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from api.state import shared_state
from config.settings import TOPIC_COMMANDS
from geo.poi import load_hydrants, load_stations
from geo.traffic import SimulatedTrafficProvider, get_zones_with_congestion

router = APIRouter()

_traffic = SimulatedTrafficProvider()


@router.get("/{vehicle_id}/route")
def get_active_route(vehicle_id: str):
    """Ruta activa del vehículo (coords, ETA, progreso)."""
    route_data = shared_state.get_route(vehicle_id)
    if not route_data:
        return {"vehicle_id": vehicle_id, "active": False, "coords": []}
    return {"vehicle_id": vehicle_id, "active": True, **route_data}


@router.get("/poi/hydrants")
def get_hydrants():
    """Posiciones de hidrantes de Valencia."""
    hydrants = load_hydrants()
    return {"count": len(hydrants), "hydrants": hydrants}


@router.get("/poi/stations")
def get_stations():
    """Estaciones de bomberos de Valencia."""
    stations = load_stations()
    return {"count": len(stations), "stations": stations}


@router.get("/traffic/current")
def get_current_traffic():
    """Factor de congestión actual simulado."""
    factor = _traffic.congestion_factor()
    return {
        "congestion_factor": factor,
        "description": _traffic.describe(factor),
    }


@router.get("/traffic/zones")
def get_traffic_zones():
    """Zonas de tráfico simulado con nivel de congestión por zona."""
    zones = get_zones_with_congestion()
    factor = _traffic.congestion_factor()
    for z in zones:
        z["description"] = _traffic.describe(z["congestion_factor"])
    return {
        "global_factor": factor,
        "global_description": _traffic.describe(factor),
        "zones": zones,
    }


@router.post("/force-emergency")
def force_emergency():
    """Envía comando al simulador para forzar una emergencia inmediata."""
    shared_state.client.publish(
        TOPIC_COMMANDS,
        json.dumps({"command": "force_emergency"}),
        qos=1,
    )
    return {"status": "ok", "message": "Comando de emergencia enviado"}


class ControlCommand(BaseModel):
    command: str
    speed_factor: Optional[float] = None


@router.post("/control")
def control_simulation(cmd: ControlCommand):
    """Control de simulacion: pause/resume/reset_mission/set_speed."""
    payload = cmd.dict()
    shared_state.client.publish(
        TOPIC_COMMANDS,
        json.dumps(payload),
        qos=1,
    )
    return {"status": "ok", "command": cmd.command}
