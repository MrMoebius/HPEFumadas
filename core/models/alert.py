"""Modelo de datos para alertas."""

from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class Alert(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    vehicle_id: str = "BOM-001"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    severity: str = "info"          # "info" | "warning" | "critical"
    category: str = "operativa"     # "mecanica" | "equipamiento" | "operativa"
    message: str = ""
    metric: str = ""
    current_value: float = 0.0
    threshold: float = 0.0
    recommended_action: str = ""
