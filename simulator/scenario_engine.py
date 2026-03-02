"""
Motor de escenarios "What-If" para el camión de bomberos.
Permite simular situaciones críticas de forma controlada.
"""

import copy
import json
import random
from loguru import logger


SCENARIOS = {
    "pump_failure_during_fire": {
        "description": "La bomba de agua falla durante un incendio activo",
        "parameters": {
            "initial_pump_pressure": 150,
            "pressure_drop_rate": 5.0,
            "fire_intensity": "alto",
            "backup_pump_available": True,
        },
    },
    "multi_fire_saturation": {
        "description": "3 incendios simultáneos con solo 2 unidades disponibles",
        "parameters": {
            "fires": 3,
            "available_units": 2,
            "severity_levels": ["structural", "vehicle", "wildfire"],
        },
    },
    "ladder_hydraulic_failure": {
        "description": "La escalera hidráulica falla durante rescate en altura",
        "parameters": {
            "equipment": "hydraulic_ladder",
            "failure_type": "hydraulic_pressure_loss",
            "rescue_height_meters": 25,
            "people_stranded": 4,
        },
    },
}


class ScenarioEngine:
    def __init__(self):
        self.active_scenario = None
        self.scenario_tick = 0
        self.results = []

    def list_scenarios(self) -> dict:
        return {k: v["description"] for k, v in SCENARIOS.items()}

    def start_scenario(self, scenario_name: str, vehicle_state: dict) -> dict:
        if scenario_name not in SCENARIOS:
            return {"error": f"Escenario '{scenario_name}' no encontrado"}

        self.active_scenario = scenario_name
        self.scenario_tick = 0
        self.results = []

        scenario = SCENARIOS[scenario_name]
        logger.info(f"Iniciando escenario: {scenario['description']}")

        return {
            "scenario": scenario_name,
            "description": scenario["description"],
            "parameters": scenario["parameters"],
            "initial_state": {
                "water_tank_level": vehicle_state.get("water_tank_level", 100),
                "pump_pressure": vehicle_state.get("pump_pressure", 150),
                "hydraulic_pressure": vehicle_state.get("hydraulic_pressure", 150),
                "ladder_status": vehicle_state.get("ladder_status", "retracted"),
            },
        }

    def simulate_pump_failure(self, state: dict) -> list[dict]:
        """Simula fallo de bomba paso a paso."""
        params = SCENARIOS["pump_failure_during_fire"]["parameters"]
        steps = []
        sim_state = copy.deepcopy(state)
        pressure = params["initial_pump_pressure"]

        for tick in range(30):
            pressure -= params["pressure_drop_rate"] + random.uniform(0, 2)
            pressure = max(0, pressure)
            sim_state["pump_pressure"] = round(pressure, 1)
            sim_state["water_tank_level"] = max(
                0, sim_state["water_tank_level"] - 0.2
            )

            alerts = []
            if pressure < 80:
                alerts.append("WARNING: Presión de bomba baja")
            if pressure < 30:
                alerts.append("CRITICAL: Fallo de bomba inminente")
            if pressure == 0:
                alerts.append("CRITICAL: Bomba fuera de servicio")

            decisions = []
            if pressure < 50 and params["backup_pump_available"]:
                decisions.append("Activar bomba auxiliar")
            if pressure == 0:
                decisions.append("Solicitar unidad de respaldo")
                decisions.append("Evacuar zona si no hay respaldo en 5 min")

            step = {
                "tick": tick,
                "pump_pressure": sim_state["pump_pressure"],
                "water_flow_active": pressure > 10,
                "water_tank_level": round(sim_state["water_tank_level"], 1),
                "alerts": alerts,
                "decisions": decisions,
            }
            steps.append(step)

            if pressure == 0:
                break

        return steps

    def simulate_ladder_failure(self, state: dict) -> list[dict]:
        """Simula fallo hidráulico de la escalera."""
        params = SCENARIOS["ladder_hydraulic_failure"]["parameters"]
        steps = []
        hydraulic = state.get("hydraulic_pressure", 150)

        for tick in range(20):
            hydraulic -= random.uniform(5, 15)
            hydraulic = max(0, hydraulic)

            alerts = []
            decisions = []

            if hydraulic < 100:
                alerts.append("WARNING: Presión hidráulica descendiendo")
            if hydraulic < 60:
                alerts.append("CRITICAL: Fallo hidráulico de escalera")
                decisions.append("Iniciar retracción manual de escalera")
                decisions.append("No desplegar más la escalera")
            if hydraulic < 30:
                alerts.append("CRITICAL: Escalera inestable")
                decisions.append(
                    f"Evacuar {params['people_stranded']} personas por vía alternativa"
                )
                decisions.append("Solicitar unidad con escalera operativa")

            step = {
                "tick": tick,
                "hydraulic_pressure": round(hydraulic, 1),
                "ladder_stable": hydraulic > 40,
                "rescue_height_meters": params["rescue_height_meters"],
                "people_stranded": params["people_stranded"],
                "alerts": alerts,
                "decisions": decisions,
            }
            steps.append(step)

            if hydraulic == 0:
                break

        return steps

    def simulate_multi_fire(self) -> dict:
        """Simula saturación por múltiples incendios."""
        params = SCENARIOS["multi_fire_saturation"]["parameters"]
        fires = []
        for i, severity in enumerate(params["severity_levels"]):
            fires.append({
                "fire_id": i + 1,
                "severity": severity,
                "location": {
                    "lat": 39.47 + random.uniform(-0.02, 0.02),
                    "lon": -0.376 + random.uniform(-0.02, 0.02),
                },
                "estimated_units_needed": 2 if severity == "structural" else 1,
            })

        total_needed = sum(f["estimated_units_needed"] for f in fires)
        deficit = total_needed - params["available_units"]

        decisions = []
        if deficit > 0:
            decisions.append(f"Déficit de {deficit} unidades — solicitar refuerzos")
            # Priorizar por severidad
            priority = sorted(fires, key=lambda f: {
                "structural": 0, "wildfire": 1, "vehicle": 2
            }.get(f["severity"], 3))
            decisions.append(
                f"Prioridad: Fuego #{priority[0]['fire_id']} ({priority[0]['severity']})"
            )
            decisions.append("Redirigir unidad HAZMAT si fuego químico detectado")

        return {
            "fires": fires,
            "available_units": params["available_units"],
            "total_units_needed": total_needed,
            "deficit": deficit,
            "decisions": decisions,
        }

    def run_scenario(self, scenario_name: str, vehicle_state: dict) -> dict:
        """Ejecuta un escenario completo y retorna resultados."""
        info = self.start_scenario(scenario_name, vehicle_state)
        if "error" in info:
            return info

        if scenario_name == "pump_failure_during_fire":
            steps = self.simulate_pump_failure(vehicle_state)
            info["simulation_steps"] = steps
            info["summary"] = {
                "total_ticks": len(steps),
                "pump_failed_at_tick": next(
                    (s["tick"] for s in steps if s["pump_pressure"] == 0),
                    None,
                ),
                "final_water_level": steps[-1]["water_tank_level"],
            }

        elif scenario_name == "ladder_hydraulic_failure":
            steps = self.simulate_ladder_failure(vehicle_state)
            info["simulation_steps"] = steps
            info["summary"] = {
                "total_ticks": len(steps),
                "ladder_unstable_at_tick": next(
                    (s["tick"] for s in steps if not s["ladder_stable"]),
                    None,
                ),
            }

        elif scenario_name == "multi_fire_saturation":
            result = self.simulate_multi_fire()
            info["simulation_result"] = result
            info["summary"] = {
                "fires": len(result["fires"]),
                "deficit": result["deficit"],
            }

        logger.info(f"Escenario completado: {scenario_name}")
        return info
