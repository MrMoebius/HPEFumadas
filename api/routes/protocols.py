"""Endpoints de protocolos de interoperabilidad (CAP, ICS, EMSI)."""

from fastapi import APIRouter, HTTPException
from api.state import shared_state
from core.models.protocols import CAPAlert, ICSIncident, EMSIMessage

router = APIRouter()


@router.get("/cap/alerts/{vehicle_id}")
def get_cap_alerts(vehicle_id: str):
    """Alertas activas en formato CAP (Common Alerting Protocol v1.2)."""
    alerts = shared_state.get_alerts()
    cap_alerts = [CAPAlert.from_alert(a).model_dump() for a in alerts]
    return {
        "protocol": "CAP",
        "version": "1.2",
        "vehicle_id": vehicle_id,
        "count": len(cap_alerts),
        "alerts": cap_alerts,
    }


@router.get("/ics/incident/{vehicle_id}")
def get_ics_incident(vehicle_id: str):
    """Estado del incidente en formato ICS/NIMS."""
    state = shared_state.get_state()
    if not state:
        raise HTTPException(status_code=503, detail="Sin datos de telemetria")
    incident = ICSIncident.from_mission(state)
    return {
        "protocol": "ICS/NIMS",
        "vehicle_id": vehicle_id,
        "incident": incident.model_dump(),
    }


@router.get("/emsi/message/{vehicle_id}")
def get_emsi_message(vehicle_id: str):
    """Estado operativo en formato EMSI (Emergency Management Shared Information)."""
    state = shared_state.get_state()
    if not state:
        raise HTTPException(status_code=503, detail="Sin datos de telemetria")
    message = EMSIMessage.from_state(state)
    return {
        "protocol": "EMSI",
        "vehicle_id": vehicle_id,
        "message": message.model_dump(),
    }


@router.get("/summary/{vehicle_id}")
def get_protocols_summary(vehicle_id: str):
    """Resumen de protocolos de interoperabilidad disponibles."""
    return {
        "vehicle_id": vehicle_id,
        "protocols": [
            {
                "name": "CAP",
                "version": "1.2",
                "description": "Common Alerting Protocol — Alertas estandarizadas",
                "endpoint": f"/api/v1/protocols/cap/alerts/{vehicle_id}",
            },
            {
                "name": "ICS/NIMS",
                "version": "NIMS 2017",
                "description": "Incident Command System — Estructura de mando",
                "endpoint": f"/api/v1/protocols/ics/incident/{vehicle_id}",
            },
            {
                "name": "EMSI",
                "version": "1.0",
                "description": "Emergency Management Shared Information — Interagencia",
                "endpoint": f"/api/v1/protocols/emsi/message/{vehicle_id}",
            },
        ],
    }
