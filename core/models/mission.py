"""Modelo de datos para misiones."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Mission(BaseModel):
    mission_id: str = ""
    vehicle_id: str = "BOM-001"
    status: str = "disponible"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    destination: str = ""
    destination_lat: float = 0.0
    destination_lon: float = 0.0
    description: str = ""
