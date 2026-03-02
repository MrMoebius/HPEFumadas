"""
Motor de reglas para generar alertas basadas en umbrales.
Evalúa cada telemetría contra reglas predefinidas.
"""

from core.models.alert import Alert


# Definición de reglas: (métrica, condición, severidad, categoría, mensaje, acción)
RULES = [
    # Motor
    {
        "metric": "engine_temp",
        "condition": lambda v: v > 105,
        "severity": "warning",
        "category": "mecanica",
        "message": "Temperatura del motor elevada",
        "threshold": 105,
        "action": "Monitorear temperatura, reducir carga del motor",
    },
    {
        "metric": "engine_temp",
        "condition": lambda v: v > 115,
        "severity": "critical",
        "category": "mecanica",
        "message": "Sobrecalentamiento del motor",
        "threshold": 115,
        "action": "Reducir operación de bomba, solicitar relevo",
    },
    # Bomba de agua
    {
        "metric": "pump_pressure",
        "condition": lambda v, m: v < 80 and v > 0 and m.get("mission_status") == "en_escena",
        "severity": "warning",
        "category": "equipamiento",
        "message": "Presión de bomba baja",
        "threshold": 80,
        "action": "Verificar bomba, preparar bomba auxiliar",
        "needs_context": True,
    },
    {
        "metric": "pump_pressure",
        "condition": lambda v, m: v < 30 and v > 0 and m.get("mission_status") == "en_escena",
        "severity": "critical",
        "category": "equipamiento",
        "message": "Fallo de bomba de agua",
        "threshold": 30,
        "action": "Activar bomba auxiliar, solicitar unidad de respaldo",
        "needs_context": True,
    },
    # Agua
    {
        "metric": "water_tank_level",
        "condition": lambda v, m: v < 20 and m.get("mission_status") == "en_escena",
        "severity": "warning",
        "category": "equipamiento",
        "message": "Nivel de agua bajo",
        "threshold": 20,
        "action": "Optimizar uso de agua, preparar solicitud de cisterna",
        "needs_context": True,
    },
    {
        "metric": "water_tank_level",
        "condition": lambda v, m: v < 15 and m.get("mission_status") == "en_escena",
        "severity": "critical",
        "category": "equipamiento",
        "message": "Agua crítica en incendio activo",
        "threshold": 15,
        "action": "Solicitar cisterna de apoyo",
        "needs_context": True,
    },
    # Espuma
    {
        "metric": "foam_tank_level",
        "condition": lambda v: v < 20,
        "severity": "warning",
        "category": "equipamiento",
        "message": "Nivel de espuma bajo",
        "threshold": 20,
        "action": "Alertar central, redirigir unidad HAZMAT si fuego químico",
    },
    # Hidráulica
    {
        "metric": "hydraulic_pressure",
        "condition": lambda v, m: v < 100 and m.get("ladder_status") == "extended",
        "severity": "warning",
        "category": "equipamiento",
        "message": "Presión hidráulica descendiendo",
        "threshold": 100,
        "action": "No desplegar más la escalera",
        "needs_context": True,
    },
    {
        "metric": "hydraulic_pressure",
        "condition": lambda v, m: v < 60 and m.get("ladder_status") == "extended",
        "severity": "critical",
        "category": "equipamiento",
        "message": "Presión hidráulica baja — escalera inestable",
        "threshold": 60,
        "action": "Retracción manual, no desplegar más",
        "needs_context": True,
    },
    # Batería
    {
        "metric": "battery_voltage",
        "condition": lambda v: v < 11.8,
        "severity": "warning",
        "category": "mecanica",
        "message": "Voltaje de batería bajo",
        "threshold": 11.8,
        "action": "Desactivar sistemas no esenciales",
    },
    {
        "metric": "battery_voltage",
        "condition": lambda v: v < 11.0,
        "severity": "critical",
        "category": "mecanica",
        "message": "Fallo eléctrico inminente",
        "threshold": 11.0,
        "action": "Priorizar comunicaciones y bomba de agua",
    },
    # Combustible
    {
        "metric": "fuel_level",
        "condition": lambda v: v < 15,
        "severity": "warning",
        "category": "operativa",
        "message": "Combustible bajo",
        "threshold": 15,
        "action": "Planificar repostaje tras misión actual",
    },
]


class RuleEngine:
    def __init__(self):
        self.rules = RULES

    def evaluate(self, telemetry: dict) -> list[Alert]:
        """Evalúa todas las reglas contra la telemetría actual."""
        triggered_alerts = []
        vehicle_id = telemetry.get("vehicle_id", "BOM-001")

        for rule in self.rules:
            metric = rule["metric"]
            if metric not in telemetry:
                continue

            value = telemetry[metric]

            # Evaluar condición (con o sin contexto)
            try:
                if rule.get("needs_context"):
                    triggered = rule["condition"](value, telemetry)
                else:
                    triggered = rule["condition"](value)
            except Exception:
                continue

            if triggered:
                alert = Alert(
                    vehicle_id=vehicle_id,
                    severity=rule["severity"],
                    category=rule["category"],
                    message=rule["message"],
                    metric=metric,
                    current_value=float(value) if isinstance(value, (int, float)) else 0,
                    threshold=rule["threshold"],
                    recommended_action=rule["action"],
                )
                triggered_alerts.append(alert)

        return triggered_alerts
