"""Endpoints de predicción de fallos."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from fastapi import APIRouter
from ai.failure_predictor import FailurePredictor
from api.state import shared_state

router = APIRouter()
predictor = FailurePredictor()


@router.get("/{vehicle_id}/failures")
def predict_failures(vehicle_id: str):
    """Predicción de fallos basada en tendencias."""
    # Alimentar el predictor con el histórico reciente
    history = shared_state.get_history(50)
    for entry in history:
        predictor.record(entry)

    predictions = predictor.predict(vehicle_id)
    return {
        "vehicle_id": vehicle_id,
        "horizon": "200 segundos (~3.3 min)",
        "predictions": predictions,
        "data_points": len(history),
    }


@router.get("/{vehicle_id}/maintenance")
def predict_maintenance(vehicle_id: str):
    """Mantenimiento preventivo recomendado."""
    state = shared_state.get_state()
    if not state:
        return {"vehicle_id": vehicle_id, "recommendations": []}

    recommendations = []

    brake_wear = state.get("brake_wear", 0)
    if brake_wear > 60:
        recommendations.append({
            "component": "frenos",
            "urgency": "alta" if brake_wear > 80 else "media",
            "current_value": round(brake_wear, 1),
            "threshold": 85,
            "action": "Programar cambio de pastillas de freno",
        })

    fuel = state.get("fuel_level", 100)
    if fuel < 30:
        recommendations.append({
            "component": "combustible",
            "urgency": "alta" if fuel < 15 else "media",
            "current_value": round(fuel, 1),
            "threshold": 15,
            "action": "Repostar antes de próxima misión",
        })

    battery = state.get("battery_voltage", 13)
    if battery < 12.5:
        recommendations.append({
            "component": "bateria",
            "urgency": "alta" if battery < 11.5 else "baja",
            "current_value": round(battery, 2),
            "threshold": 11.5,
            "action": "Revisar alternador y estado de batería",
        })

    mileage = state.get("mileage_km", 0)
    if mileage > 0 and mileage % 10000 < 500:
        recommendations.append({
            "component": "revision_general",
            "urgency": "baja",
            "current_value": round(mileage, 0),
            "threshold": "cada 10.000 km",
            "action": "Programar revisión general del vehículo",
        })

    return {
        "vehicle_id": vehicle_id,
        "recommendations": recommendations,
        "mileage_km": round(state.get("mileage_km", 0), 1),
    }
