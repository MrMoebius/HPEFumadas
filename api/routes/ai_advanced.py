"""Endpoints de IA Avanzada — Despliegue predictivo, estimacion de recursos, optimizacion de flota."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

from ai.predictive_deployment import analyze, recommend_positions
from ai.resource_estimator import estimate, get_incident_types
from ai.fleet_optimizer import optimize, coverage_score, DEFAULT_FLEET

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────

class ResourceEstimateRequest(BaseModel):
    type: str = Field(..., description="Tipo de incidente (ej: incendio_vivienda)")
    severity: str = Field(default="media", description="Severidad: baja, media, alta")
    area_m2: Optional[float] = Field(default=200, description="Area afectada en m2")


# ── Despliegue predictivo ────────────────────────────────────────────────

@router.get("/{vehicle_id}/risk-zones")
def get_risk_zones(vehicle_id: str, hour: int = 14):
    """Zonas de riesgo segun hora del dia (KMeans clustering)."""
    result = analyze(hour)
    return {
        "vehicle_id": vehicle_id,
        **result,
    }


@router.get("/{vehicle_id}/deployment")
def get_deployment(vehicle_id: str, hour: int = 14, vehicles: int = 3):
    """Posiciones recomendadas para despliegue preventivo."""
    result = recommend_positions(hour, vehicles)
    return {
        "vehicle_id": vehicle_id,
        **result,
    }


# ── Estimacion de recursos ──────────────────────────────────────────────

@router.post("/{vehicle_id}/estimate-resources")
def estimate_resources(vehicle_id: str, body: ResourceEstimateRequest):
    """Estima recursos necesarios para un tipo de incidente (DecisionTree)."""
    result = estimate(body.type, body.severity, body.area_m2)
    return {
        "vehicle_id": vehicle_id,
        **result,
    }


@router.get("/{vehicle_id}/estimate-resources/types")
def list_incident_types(vehicle_id: str):
    """Lista tipos de incidente disponibles con descripcion."""
    return {
        "vehicle_id": vehicle_id,
        "types": get_incident_types(),
        "severities": ["baja", "media", "alta"],
    }


# ── Optimizacion de flota ───────────────────────────────────────────────

@router.get("/fleet/optimize")
def optimize_fleet():
    """Optimiza asignacion vehiculo-emergencia (algoritmo hungaro)."""
    result = optimize()
    return result


@router.get("/fleet/coverage")
def fleet_coverage():
    """Score de cobertura actual de la flota sobre zonas de riesgo."""
    result = coverage_score()
    return result
