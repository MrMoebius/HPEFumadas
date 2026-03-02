"""Modelos de datos Pydantic para el gemelo digital del camión de bomberos."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class VehicleState(BaseModel):
    # Identificación
    vehicle_id: str = "BOM-001"
    vehicle_type: str = "camion_bomberos_BUP"

    # Motor y mecánica
    engine_temp: float = 85.0
    engine_rpm: int = 800
    fuel_level: float = 95.0
    oil_pressure: float = 40.0
    battery_voltage: float = 13.2
    brake_wear: float = 15.0
    tire_pressure: dict = Field(default_factory=lambda: {
        "FL": 35.0, "FR": 35.0, "RL": 33.0, "RR": 33.0
    })
    mileage_km: float = 0.0

    # Ubicación y movimiento
    latitude: float = 39.4699
    longitude: float = -0.3763
    speed_kmh: float = 0.0
    heading: float = 0.0

    # Equipamiento contra incendios
    water_tank_level: float = 100.0
    foam_tank_level: float = 100.0
    pump_pressure: float = 0.0
    ladder_status: str = "retracted"
    ladder_angle: float = 0.0
    hose_deployed: bool = False
    hydraulic_pressure: float = 150.0
    crew_count: int = 6

    # Misión
    mission_status: str = "disponible"
    sirens_active: bool = False
    lights_active: bool = False

    # Metadatos
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    anomalies: list[str] = Field(default_factory=list)
    risk_score: float = 0.0
    tick: int = 0
