"""Endpoints del ecosistema de gemelos digitales."""

from fastapi import APIRouter
from api.state import shared_state

router = APIRouter()


@router.get("/status")
def ecosystem_status():
    """Estado del ecosistema de gemelos conectados."""
    state = shared_state.get_state()
    bom_status = "online" if state else "offline"

    return {
        "twins": [
            {
                "twin_id": "BOM-001",
                "type": "camion_bomberos_BUP",
                "status": bom_status,
                "mission_status": state.get("mission_status", "unknown") if state else "unknown",
                "last_update": state.get("timestamp", None) if state else None,
                "is_primary": True,
            },
            {
                "twin_id": "POL-001",
                "type": "patrulla_policial",
                "status": "simulated",
                "mission_status": "disponible",
                "last_update": None,
                "is_primary": False,
            },
            {
                "twin_id": "AMB-001",
                "type": "ambulancia_tipo_C",
                "status": "simulated",
                "mission_status": "disponible",
                "last_update": None,
                "is_primary": False,
            },
        ],
        "total_twins": 3,
        "online_twins": 1,
    }


@router.get("/twins")
def list_twins():
    """Lista de gemelos registrados."""
    return {
        "twins": [
            {"id": "BOM-001", "type": "Camión de Bomberos", "active": True},
            {"id": "POL-001", "type": "Patrulla Policial", "active": False},
            {"id": "AMB-001", "type": "Ambulancia", "active": False},
        ]
    }


@router.post("/event")
def send_event(event: dict):
    """Enviar evento al ecosistema (placeholder)."""
    return {
        "status": "received",
        "event": event,
        "note": "Evento registrado. Distribución a otros gemelos pendiente de implementación.",
    }
