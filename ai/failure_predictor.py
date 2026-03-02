"""
Predicción de fallos usando análisis de tendencias con statsmodels.
Analiza series temporales para predecir cuándo una métrica cruzará un umbral crítico.
"""

import numpy as np
from collections import deque
from loguru import logger

try:
    from statsmodels.tsa.holtwinters import SimpleExpSmoothing
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    logger.warning("statsmodels no disponible, usando predicción por tendencia lineal")


# Componentes a predecir
PREDICTABLE_COMPONENTS = {
    "engine_temp": {
        "critical_threshold": 115,
        "direction": "rising",
        "component_name": "motor",
    },
    "pump_pressure": {
        "critical_threshold": 30,
        "direction": "falling",
        "component_name": "bomba_agua",
    },
    "hydraulic_pressure": {
        "critical_threshold": 60,
        "direction": "falling",
        "component_name": "sistema_hidraulico",
    },
    "battery_voltage": {
        "critical_threshold": 11.0,
        "direction": "falling",
        "component_name": "bateria",
    },
    "brake_wear": {
        "critical_threshold": 85,
        "direction": "rising",
        "component_name": "frenos",
    },
}


class FailurePredictor:
    def __init__(self, window_size: int = 50, horizon_ticks: int = 100):
        self.window_size = window_size
        self.horizon_ticks = horizon_ticks  # ~200s a 2s/tick
        self.series: dict[str, deque] = {
            k: deque(maxlen=window_size) for k in PREDICTABLE_COMPONENTS
        }

    def record(self, telemetry: dict):
        """Registra valores para las series temporales."""
        for metric in PREDICTABLE_COMPONENTS:
            value = telemetry.get(metric)
            if value is not None and isinstance(value, (int, float)):
                self.series[metric].append(float(value))

    def predict(self, vehicle_id: str = "BOM-001") -> list[dict]:
        """
        Predice fallos futuros basándose en tendencias.
        Retorna lista de predicciones ordenadas por probabilidad.
        """
        predictions = []

        for metric, config in PREDICTABLE_COMPONENTS.items():
            series = list(self.series[metric])
            if len(series) < 10:
                continue

            result = self._predict_metric(series, config)
            if result:
                result["component"] = config["component_name"]
                result["metric"] = metric
                result["vehicle_id"] = vehicle_id
                predictions.append(result)

        # Ordenar por probabilidad descendente
        predictions.sort(key=lambda x: x["probability"], reverse=True)
        return predictions

    def _predict_metric(self, series: list[float], config: dict) -> dict | None:
        """Predice si una métrica cruzará su umbral crítico."""
        threshold = config["critical_threshold"]
        direction = config["direction"]
        current = series[-1]

        # Calcular tendencia
        if HAS_STATSMODELS and len(series) >= 15:
            trend = self._trend_statsmodels(series)
        else:
            trend = self._trend_linear(series)

        if trend is None:
            return None

        # ¿La tendencia va hacia el umbral?
        if direction == "rising" and trend <= 0:
            return None
        if direction == "falling" and trend >= 0:
            return None

        # Estimar ticks hasta cruzar umbral
        distance = abs(threshold - current)
        if abs(trend) < 0.001:
            return None

        ticks_to_failure = distance / abs(trend)

        if ticks_to_failure > self.horizon_ticks:
            return None

        # Probabilidad: más cerca del umbral = más probable
        probability = 1.0 - (ticks_to_failure / self.horizon_ticks)
        probability = min(max(probability, 0.0), 0.99)

        estimated_seconds = ticks_to_failure * 2  # TICK_INTERVAL = 2s

        return {
            "probability": round(probability, 2),
            "estimated_seconds": round(estimated_seconds, 0),
            "current_value": round(current, 2),
            "threshold": threshold,
            "trend_per_tick": round(trend, 4),
        }

    def _trend_statsmodels(self, series: list[float]) -> float | None:
        """Calcula tendencia usando suavizado exponencial."""
        try:
            arr = np.array(series)
            model = SimpleExpSmoothing(arr).fit(smoothing_level=0.3)
            forecast = model.forecast(5)
            trend = (forecast[-1] - arr[-1]) / 5
            return trend
        except Exception:
            return self._trend_linear(series)

    def _trend_linear(self, series: list[float]) -> float | None:
        """Calcula tendencia con regresión lineal simple."""
        n = len(series)
        if n < 5:
            return None
        x = np.arange(n)
        y = np.array(series)
        # Regresión lineal: y = mx + b
        m = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (
            n * np.sum(x**2) - np.sum(x)**2
        )
        return float(m)
