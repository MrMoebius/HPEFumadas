"""Modelo de datos para eventos de telemetría."""

from datetime import datetime
from pydantic import BaseModel, Field


class TelemetryEvent(BaseModel):
    vehicle_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metric: str
    value: float
    unit: str = ""
    source: str = "simulated"
