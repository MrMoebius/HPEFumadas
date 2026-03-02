"""Endpoints de simulación de escenarios what-if."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from simulator.scenario_engine import ScenarioEngine
from api.state import shared_state

router = APIRouter()
engine = ScenarioEngine()


class ScenarioRequest(BaseModel):
    scenario: str
    parameters: Optional[dict] = None


@router.get("/scenarios")
def list_scenarios():
    """Lista de escenarios disponibles."""
    return {
        "scenarios": engine.list_scenarios()
    }


@router.post("/scenario")
def run_scenario(request: ScenarioRequest):
    """Ejecutar un escenario what-if."""
    state = shared_state.get_state()
    if not state:
        state = {
            "water_tank_level": 80,
            "pump_pressure": 150,
            "hydraulic_pressure": 150,
            "ladder_status": "retracted",
        }

    result = engine.run_scenario(request.scenario, state)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/failure")
def simulate_failure(request: ScenarioRequest):
    """Simular un fallo específico."""
    state = shared_state.get_state()
    if not state:
        state = {
            "water_tank_level": 80,
            "pump_pressure": 150,
            "hydraulic_pressure": 150,
            "ladder_status": "retracted",
        }

    result = engine.run_scenario(request.scenario, state)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
