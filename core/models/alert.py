"""Modelo de datos para alertas con ciclo de vida y auto-escalación."""

from datetime import datetime
from pydantic import BaseModel, Field
import uuid


# Mapeo de severidades antiguas a nuevas
SEVERITY_MIGRATION = {
    "info": "informativa",
    "warning": "advertencia",
    "critical": "critica",
}

SEVERITY_LEVELS = ["informativa", "advertencia", "critica", "emergencia"]

# Timeouts de auto-escalación por severidad (segundos)
ESCALATION_TIMEOUTS = {
    "informativa": 120,
    "advertencia": 60,
    "critica": 30,
}

STATUS_VALUES = ["activa", "confirmada", "escalada", "descartada", "resuelta"]


class Alert(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    vehicle_id: str = "BOM-001"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    severity: str = "informativa"
    original_severity: str = ""
    category: str = "operativa"       # mecanica | equipamiento | operativa | seguridad
    message: str = ""
    metric: str = ""
    current_value: float = 0.0
    threshold: float = 0.0
    recommended_action: str = ""
    status: str = "activa"            # activa | confirmada | escalada | descartada | resuelta
    confirmed_by: str = ""
    confirmed_at: datetime | None = None
    escalation_count: int = 0
    history: list[dict] = Field(default_factory=list)

    def model_post_init(self, __context):
        # Migrar severidades antiguas
        if self.severity in SEVERITY_MIGRATION:
            self.severity = SEVERITY_MIGRATION[self.severity]
        if not self.original_severity:
            self.original_severity = self.severity

    def needs_escalation(self) -> bool:
        """Comprueba si la alerta necesita escalación por timeout."""
        if self.status not in ("activa", "escalada"):
            return False
        if self.severity == "emergencia":
            return False
        timeout = ESCALATION_TIMEOUTS.get(self.severity)
        if timeout is None:
            return False
        elapsed = (datetime.utcnow() - self.timestamp).total_seconds()
        return elapsed > timeout

    def escalate(self) -> bool:
        """Escala la alerta al siguiente nivel de severidad."""
        idx = SEVERITY_LEVELS.index(self.severity)
        if idx >= len(SEVERITY_LEVELS) - 1:
            return False
        prev = self.severity
        self.severity = SEVERITY_LEVELS[idx + 1]
        self.status = "escalada"
        self.escalation_count += 1
        self.timestamp = datetime.utcnow()  # reset timeout
        self.history.append({
            "action": "escalada",
            "from": prev,
            "to": self.severity,
            "at": datetime.utcnow().isoformat(),
        })
        return True

    def confirm(self, operator: str = "operador") -> None:
        """Confirma la alerta (ACK)."""
        self.status = "confirmada"
        self.confirmed_by = operator
        self.confirmed_at = datetime.utcnow()
        self.history.append({
            "action": "confirmada",
            "by": operator,
            "at": datetime.utcnow().isoformat(),
        })

    def dismiss(self, operator: str = "operador") -> None:
        """Descarta la alerta."""
        self.status = "descartada"
        self.confirmed_by = operator
        self.confirmed_at = datetime.utcnow()
        self.history.append({
            "action": "descartada",
            "by": operator,
            "at": datetime.utcnow().isoformat(),
        })

    def resolve(self) -> None:
        """Resuelve la alerta (métrica volvió a rango normal)."""
        self.status = "resuelta"
        self.history.append({
            "action": "resuelta",
            "at": datetime.utcnow().isoformat(),
        })
