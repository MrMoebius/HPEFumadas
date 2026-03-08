"""Endpoints REST para cartografia, rutas activas, POIs, trafico, emergencias y control."""

import json
import os
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from api.state import shared_state
from config.settings import TOPIC_COMMANDS
from geo.poi import load_hydrants, load_stations, list_cities
from geo.traffic import SimulatedTrafficProvider, get_zones_with_congestion

router = APIRouter()

_traffic = SimulatedTrafficProvider()

_EMERGENCIES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "simulator", "data", "emergencies.json"
)


@router.get("/{vehicle_id}/route")
def get_active_route(vehicle_id: str):
    """Ruta activa del vehiculo (coords, ETA, progreso)."""
    route_data = shared_state.get_route(vehicle_id)
    if not route_data:
        return {"vehicle_id": vehicle_id, "active": False, "coords": []}
    return {"vehicle_id": vehicle_id, "active": True, **route_data}


@router.get("/{vehicle_id}/emergency")
def get_active_emergency(vehicle_id: str):
    """Emergencia activa del vehiculo."""
    emergency = shared_state.get_active_emergency()
    if not emergency:
        return {"vehicle_id": vehicle_id, "active": False}
    return {"vehicle_id": vehicle_id, "active": True, **emergency}


@router.get("/poi/hydrants")
def get_hydrants(city: Optional[str] = None):
    """Posiciones de hidrantes, filtrables por ciudad."""
    hydrants = load_hydrants()
    if city:
        hydrants = [h for h in hydrants if h.get("city", "Valencia") == city]
    return {"count": len(hydrants), "hydrants": hydrants}


@router.get("/poi/stations")
def get_stations(city: Optional[str] = None):
    """Estaciones de bomberos, filtrables por ciudad."""
    stations = load_stations()
    if city:
        stations = [s for s in stations if s.get("city", "Valencia") == city]
    return {"count": len(stations), "stations": stations}


@router.get("/cities")
def get_cities():
    """Lista de ciudades soportadas para POIs."""
    cities = list_cities()
    return {"count": len(cities), "cities": cities}


@router.get("/emergencies")
def list_emergencies(city: Optional[str] = None):
    """Ubicaciones de emergencia predefinidas, filtrables por ciudad."""
    try:
        with open(_EMERGENCIES_PATH, "r", encoding="utf-8") as f:
            all_data = json.load(f)
    except Exception:
        return {"count": 0, "emergencies": []}

    if city:
        emergencies = all_data.get(city, [])
    else:
        emergencies = []
        for items in all_data.values():
            emergencies.extend(items)
    return {"count": len(emergencies), "emergencies": emergencies}


@router.get("/traffic/current")
def get_current_traffic():
    """Factor de congestion actual simulado."""
    factor = _traffic.congestion_factor()
    return {
        "congestion_factor": factor,
        "description": _traffic.describe(factor),
    }


@router.get("/traffic/zones")
def get_traffic_zones(city: Optional[str] = None):
    """Zonas de trafico simulado con nivel de congestion por zona."""
    zones = get_zones_with_congestion(city=city or "Valencia")
    factor = _traffic.congestion_factor()
    for z in zones:
        z["description"] = _traffic.describe(z["congestion_factor"])
    return {
        "global_factor": factor,
        "global_description": _traffic.describe(factor),
        "zones": zones,
    }


class EmergencyDispatchRequest(BaseModel):
    emergency_type: Optional[str] = None
    destination_lat: Optional[float] = None
    destination_lon: Optional[float] = None
    destination_name: Optional[str] = None


@router.post("/force-emergency")
def force_emergency(body: EmergencyDispatchRequest = EmergencyDispatchRequest()):
    """Despacha una emergencia. Sin parametros = emergencia aleatoria."""
    payload = {"command": "force_emergency"}
    if body.emergency_type:
        payload["emergency_type"] = body.emergency_type
    if body.destination_lat is not None and body.destination_lon is not None:
        payload["destination_lat"] = body.destination_lat
        payload["destination_lon"] = body.destination_lon
    if body.destination_name:
        payload["destination_name"] = body.destination_name

    shared_state.client.publish(
        TOPIC_COMMANDS,
        json.dumps(payload),
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
