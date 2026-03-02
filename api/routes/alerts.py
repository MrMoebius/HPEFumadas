"""Endpoints de alertas y anomalías."""

from fastapi import APIRouter, Query
from api.state import shared_state

router = APIRouter()


@router.get("/alerts/{vehicle_id}")
def get_active_alerts(vehicle_id: str):
    """Alertas activas del vehículo."""
    alerts = shared_state.get_alerts()
    return {
        "vehicle_id": vehicle_id,
        "count": len(alerts),
        "alerts": alerts,
    }


@router.get("/alerts/{vehicle_id}/history")
def get_alerts_history(vehicle_id: str, limit: int = Query(50, ge=1, le=200)):
    """Histórico de alertas desde SQLite."""
    alerts = shared_state.get_alerts_from_db(limit)
    return {
        "vehicle_id": vehicle_id,
        "count": len(alerts),
        "alerts": alerts,
    }


@router.get("/anomalies/{vehicle_id}")
def get_anomalies(vehicle_id: str):
    """Anomalías detectadas actualmente."""
    state = shared_state.get_state()
    anomalies = state.get("anomalies", [])
    risk_score = state.get("risk_score", 0)
    return {
        "vehicle_id": vehicle_id,
        "anomalies": anomalies,
        "risk_score": risk_score,
        "count": len(anomalies),
    }
