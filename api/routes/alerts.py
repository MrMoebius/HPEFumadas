"""Endpoints de alertas, anomalías, acciones sobre alertas y chat."""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from api.state import shared_state

router = APIRouter()


# ── Alertas existentes ─────────────────────────────────────────────────────

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


# ── Acciones sobre alertas ─────────────────────────────────────────────────

@router.post("/alerts/{vehicle_id}/{alert_id}/confirm")
def confirm_alert(vehicle_id: str, alert_id: str, operator: str = "operador"):
    """Confirma (ACK) una alerta activa."""
    shared_state.confirm_alert(vehicle_id, alert_id, operator)
    return {"status": "ok", "action": "confirmed", "alert_id": alert_id}


@router.post("/alerts/{vehicle_id}/{alert_id}/escalate")
def escalate_alert(vehicle_id: str, alert_id: str, operator: str = "operador"):
    """Escala manualmente una alerta."""
    shared_state.escalate_alert(vehicle_id, alert_id, operator)
    return {"status": "ok", "action": "escalated", "alert_id": alert_id}


@router.post("/alerts/{vehicle_id}/{alert_id}/dismiss")
def dismiss_alert(vehicle_id: str, alert_id: str, operator: str = "operador"):
    """Descarta una alerta activa."""
    shared_state.dismiss_alert(vehicle_id, alert_id, operator)
    return {"status": "ok", "action": "dismissed", "alert_id": alert_id}


# ── Chat ───────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    sender: str = "operador"
    message: str
    role: str = "operador"


@router.post("/chat/{vehicle_id}/send")
def send_chat(vehicle_id: str, body: ChatMessage):
    """Envía un mensaje de chat al vehículo."""
    shared_state.send_chat(body.sender, body.message, body.role)
    return {"status": "ok", "vehicle_id": vehicle_id}


@router.get("/chat/{vehicle_id}/messages")
def get_chat(vehicle_id: str, limit: int = Query(50, ge=1, le=200)):
    """Obtiene mensajes de chat recientes."""
    messages = shared_state.get_chat(limit)
    return {
        "vehicle_id": vehicle_id,
        "count": len(messages),
        "messages": messages,
    }
