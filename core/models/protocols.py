"""
Modelos de protocolos de interoperabilidad de emergencias.
- CAP (Common Alerting Protocol v1.2)
- ICS (NIMS/Incident Command System)
- EMSI (Emergency Management Shared Information)
"""

from datetime import datetime
from pydantic import BaseModel, Field
import uuid


# ════════════════════════════════════════════════════════════════════════════
#  CAP — Common Alerting Protocol v1.2
# ════════════════════════════════════════════════════════════════════════════

CAP_SEVERITY_MAP = {
    "informativa": "Minor",
    "advertencia": "Moderate",
    "critica": "Severe",
    "emergencia": "Extreme",
    # Compat
    "info": "Minor",
    "warning": "Moderate",
    "critical": "Severe",
}

CAP_CATEGORY_MAP = {
    "mecanica": "Transport",
    "equipamiento": "Fire",
    "operativa": "Fire",
    "seguridad": "Safety",
}


class CAPAlert(BaseModel):
    """Common Alerting Protocol v1.2 alert message."""
    identifier: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = "bomberos-valencia-dt"
    sent: str = Field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S-00:00"))
    status: str = "Actual"
    msgType: str = "Alert"
    scope: str = "Restricted"
    category: str = "Fire"
    event: str = ""
    urgency: str = "Immediate"
    severity: str = "Moderate"
    certainty: str = "Observed"
    headline: str = ""
    description: str = ""
    instruction: str = ""
    area: str = "Valencia, Spain"

    @classmethod
    def from_alert(cls, alert: dict) -> "CAPAlert":
        sev = alert.get("severity", "informativa")
        cat = alert.get("category", "operativa")
        metric = alert.get("metric", "")
        value = alert.get("current_value", 0)
        threshold = alert.get("threshold", 0)

        return cls(
            identifier=alert.get("alert_id", str(uuid.uuid4())[:8]),
            event=alert.get("message", "Alerta del sistema"),
            severity=CAP_SEVERITY_MAP.get(sev, "Moderate"),
            category=CAP_CATEGORY_MAP.get(cat, "Fire"),
            headline=alert.get("message", ""),
            description=f"Metrica: {metric}, Valor: {value}, Umbral: {threshold}",
            instruction=alert.get("recommended_action", ""),
        )


# ════════════════════════════════════════════════════════════════════════════
#  ICS — NIMS/Incident Command System
# ════════════════════════════════════════════════════════════════════════════

class ICSRole(BaseModel):
    """Rol dentro de la estructura ICS."""
    position: str
    name: str = ""
    status: str = "active"


class ICSIncident(BaseModel):
    """Incidente en formato ICS/NIMS."""
    incident_id: str = Field(default_factory=lambda: f"INC-{str(uuid.uuid4())[:6].upper()}")
    incident_name: str = ""
    incident_type: str = "Structure Fire"
    status: str = "Active"
    start_time: str = ""
    command_structure: list[ICSRole] = Field(default_factory=list)
    resources_assigned: int = 0
    location: str = ""
    latitude: float = 0.0
    longitude: float = 0.0

    @classmethod
    def from_mission(cls, state: dict) -> "ICSIncident":
        mission = state.get("mission_status", "disponible")
        crew = state.get("crew_count", 0)

        status_map = {
            "disponible": "Standby",
            "en_ruta": "En Route",
            "en_escena": "Active",
            "regreso_base": "Returning",
        }

        # Estructura de mando basica
        command = [
            ICSRole(position="Incident Commander", name="Jefe de Dotacion"),
            ICSRole(position="Operations Chief", name="Jefe de Operaciones"),
            ICSRole(position="Safety Officer", name="Oficial de Seguridad"),
        ]

        return cls(
            incident_name=f"Intervencion {state.get('vehicle_id', 'BOM-001')}",
            status=status_map.get(mission, "Unknown"),
            start_time=state.get("timestamp", ""),
            command_structure=command,
            resources_assigned=crew,
            location=f"{state.get('latitude', 0):.6f}, {state.get('longitude', 0):.6f}",
            latitude=state.get("latitude", 0),
            longitude=state.get("longitude", 0),
        )


# ════════════════════════════════════════════════════════════════════════════
#  EMSI — Emergency Management Shared Information
# ════════════════════════════════════════════════════════════════════════════

class EMSIContext(BaseModel):
    """Contexto EMSI del incidente."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    mode: str = "ACTUAL"
    msgType: str = "REPORT"
    seclass: str = "RESTRICTED"
    freeText: str = ""


class EMSIEvent(BaseModel):
    """Evento EMSI."""
    id: str = Field(default_factory=lambda: f"EVT-{str(uuid.uuid4())[:6].upper()}")
    name: str = ""
    mainType: str = "FIRE"
    subType: str = "STRUCTURE"
    status: str = "ONGOING"
    urgency: str = "URGENT"
    severity: str = "MODERATE"
    latitude: float = 0.0
    longitude: float = 0.0


class EMSIResource(BaseModel):
    """Recurso EMSI."""
    id: str = ""
    name: str = ""
    type: str = "VEHICLE"
    subType: str = "FIRE_ENGINE"
    status: str = "AVAILABLE"
    crew_count: int = 0
    water_level_pct: float = 100.0
    fuel_level_pct: float = 100.0


class EMSIMessage(BaseModel):
    """Mensaje EMSI completo."""
    context: EMSIContext = Field(default_factory=EMSIContext)
    event: EMSIEvent = Field(default_factory=EMSIEvent)
    resources: list[EMSIResource] = Field(default_factory=list)

    @classmethod
    def from_state(cls, state: dict) -> "EMSIMessage":
        mission = state.get("mission_status", "disponible")

        status_map = {
            "disponible": "AVAILABLE",
            "en_ruta": "EN_ROUTE",
            "en_escena": "ON_SCENE",
            "regreso_base": "RETURNING",
        }
        urgency_map = {
            "disponible": "ROUTINE",
            "en_ruta": "URGENT",
            "en_escena": "IMMEDIATE",
            "regreso_base": "ROUTINE",
        }

        context = EMSIContext(
            freeText=f"Gemelo Digital {state.get('vehicle_id', 'BOM-001')} - Estado operativo",
        )

        event = EMSIEvent(
            name=f"Operacion {state.get('vehicle_id', 'BOM-001')}",
            status="ONGOING" if mission in ("en_ruta", "en_escena") else "STANDBY",
            urgency=urgency_map.get(mission, "ROUTINE"),
            latitude=state.get("latitude", 0),
            longitude=state.get("longitude", 0),
        )

        resource = EMSIResource(
            id=state.get("vehicle_id", "BOM-001"),
            name=f"Camion Bomberos {state.get('vehicle_id', 'BOM-001')}",
            status=status_map.get(mission, "UNKNOWN"),
            crew_count=state.get("crew_count", 0),
            water_level_pct=state.get("water_tank_level", 100),
            fuel_level_pct=state.get("fuel_level", 100),
        )

        return cls(
            context=context,
            event=event,
            resources=[resource],
        )
