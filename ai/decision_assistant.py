"""
Asistente de decisiones basado en reglas + scoring.
Evalúa el estado del vehículo y recomienda acciones operativas.
"""

from loguru import logger


# Tabla de decisiones: condición → decisión
DECISION_RULES = [
    {
        "id": "water_critical",
        "condition": lambda t: (
            t.get("water_tank_level", 100) < 15
            and t.get("mission_status") == "en_escena"
        ),
        "decision": "Solicitar cisterna de apoyo",
        "priority": "critical",
    },
    {
        "id": "engine_overheat",
        "condition": lambda t: t.get("engine_temp", 85) > 110,
        "decision": "Reducir operación de bomba, solicitar relevo",
        "priority": "critical",
    },
    {
        "id": "foam_low_chemical",
        "condition": lambda t: t.get("foam_tank_level", 100) < 20,
        "decision": "Alertar central, redirigir unidad HAZMAT",
        "priority": "high",
    },
    {
        "id": "pump_failure",
        "condition": lambda t: (
            0 < t.get("pump_pressure", 150) < 30
            and t.get("mission_status") == "en_escena"
        ),
        "decision": "Activar bomba auxiliar, solicitar unidad de respaldo",
        "priority": "critical",
    },
    {
        "id": "hydraulic_low",
        "condition": lambda t: (
            t.get("hydraulic_pressure", 150) < 80
            and t.get("ladder_status") == "extended"
        ),
        "decision": "Retracción manual de escalera, no desplegar más",
        "priority": "critical",
    },
    {
        "id": "multi_anomaly",
        "condition": lambda t: len(t.get("anomalies", [])) >= 2,
        "decision": "Evacuar equipo del vehículo, enviar reemplazo",
        "priority": "critical",
    },
    {
        "id": "fuel_low_mission",
        "condition": lambda t: (
            t.get("fuel_level", 100) < 15
            and t.get("mission_status") in ("en_ruta", "en_escena")
        ),
        "decision": "Planificar repostaje inmediato tras misión",
        "priority": "high",
    },
    {
        "id": "battery_low",
        "condition": lambda t: t.get("battery_voltage", 13) < 11.5,
        "decision": "Desactivar sistemas no esenciales, priorizar comunicaciones",
        "priority": "high",
    },
]


class DecisionAssistant:
    def __init__(self):
        self.active_decisions: dict[str, str] = {}
        self._previous_ids: set[str] = set()

    def evaluate(self, telemetry: dict) -> list[str]:
        """
        Evalúa el estado y retorna decisiones activadas.
        Solo retorna decisiones nuevas (no repite las ya activas).
        """
        current_ids = set()
        new_decisions = []

        for rule in DECISION_RULES:
            try:
                if rule["condition"](telemetry):
                    current_ids.add(rule["id"])
                    if rule["id"] not in self._previous_ids:
                        decision_text = f"[{rule['priority'].upper()}] {rule['decision']}"
                        new_decisions.append(decision_text)
                        self.active_decisions[rule["id"]] = rule["decision"]
            except Exception:
                continue

        # Limpiar decisiones que ya no aplican
        resolved = self._previous_ids - current_ids
        for rid in resolved:
            if rid in self.active_decisions:
                logger.info(f"Decisión resuelta: {self.active_decisions.pop(rid)}")

        self._previous_ids = current_ids
        return new_decisions

    def get_active_decisions(self) -> list[dict]:
        """Retorna todas las decisiones activas."""
        return [
            {"id": k, "decision": v}
            for k, v in self.active_decisions.items()
        ]
