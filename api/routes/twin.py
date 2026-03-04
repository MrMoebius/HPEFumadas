"""Endpoints del estado del gemelo digital."""

from fastapi import APIRouter, HTTPException, Query
from api.state import shared_state

router = APIRouter()


@router.get("/{vehicle_id}/state")
def get_state(vehicle_id: str):
    """Estado actual completo del vehículo."""
    state = shared_state.get_state()
    if not state:
        raise HTTPException(status_code=503, detail="Sin datos de telemetría aún")
    if state.get("vehicle_id") != vehicle_id:
        raise HTTPException(status_code=404, detail=f"Vehículo {vehicle_id} no encontrado")
    return state


@router.get("/{vehicle_id}/history")
def get_history(vehicle_id: str, limit: int = Query(100, ge=1, le=500)):
    """Histórico de estados recientes (en memoria)."""
    history = shared_state.get_history(limit)
    return {"vehicle_id": vehicle_id, "count": len(history), "history": history}


@router.get("/{vehicle_id}/health")
def get_health(vehicle_id: str):
    """Resumen de salud del vehículo."""
    state = shared_state.get_state()
    if not state:
        raise HTTPException(status_code=503, detail="Sin datos de telemetría aún")

    # Calcular health score
    issues = []
    if state.get("engine_temp", 85) > 105:
        issues.append("engine_temp_high")
    if state.get("fuel_level", 100) < 15:
        issues.append("fuel_low")
    if state.get("battery_voltage", 13) < 11.8:
        issues.append("battery_low")
    if state.get("water_tank_level", 100) < 20:
        issues.append("water_low")
    if state.get("hydraulic_pressure", 150) < 100:
        issues.append("hydraulic_low")

    health_score = max(0, 1.0 - len(issues) * 0.2)

    return {
        "vehicle_id": vehicle_id,
        "health_score": round(health_score, 2),
        "status": "healthy" if health_score > 0.7 else "degraded" if health_score > 0.3 else "critical",
        "issues": issues,
        "mission_status": state.get("mission_status", "unknown"),
        "anomalies": state.get("anomalies", []),
    }


@router.get("/{vehicle_id}/timeline")
def get_timeline(vehicle_id: str):
    """Línea de tiempo de eventos de misión y alertas."""
    mission_events = shared_state.get_mission_timeline()
    alerts = shared_state.get_alerts()

    # Combinar eventos de misión y alertas en una timeline unificada
    timeline = []

    for evt in mission_events:
        timeline.append({
            "type": "mission",
            "event": evt.get("type", "transition"),
            "from": evt.get("from", ""),
            "to": evt.get("to", ""),
            "timestamp": evt.get("timestamp", ""),
            "tick": evt.get("tick", 0),
        })

    for alert in alerts:
        timeline.append({
            "type": "alert",
            "severity": alert.get("severity", "informativa"),
            "message": alert.get("message", ""),
            "metric": alert.get("metric", ""),
            "status": alert.get("status", "activa"),
            "timestamp": alert.get("timestamp", ""),
        })

    # Ordenar por timestamp
    timeline.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return {
        "vehicle_id": vehicle_id,
        "count": len(timeline),
        "events": timeline,
    }
