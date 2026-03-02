"""
Detección de anomalías usando Isolation Forest.
Evalúa métricas numéricas para detectar comportamientos anormales.
"""

import numpy as np
from collections import deque
from loguru import logger

try:
    from sklearn.ensemble import IsolationForest
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logger.warning("scikit-learn no disponible, usando detección por umbrales")


# Métricas a monitorear y sus rangos normales
MONITORED_METRICS = {
    "engine_temp": {"min": 75, "max": 105, "unit": "°C"},
    "pump_pressure": {"min": 0, "max": 160, "unit": "PSI"},
    "water_tank_level": {"min": 10, "max": 100, "unit": "%"},
    "foam_tank_level": {"min": 10, "max": 100, "unit": "%"},
    "hydraulic_pressure": {"min": 80, "max": 170, "unit": "PSI"},
    "battery_voltage": {"min": 11.5, "max": 15.0, "unit": "V"},
    "oil_pressure": {"min": 25, "max": 65, "unit": "PSI"},
    "fuel_level": {"min": 10, "max": 100, "unit": "%"},
}

FEATURE_ORDER = list(MONITORED_METRICS.keys())


class AnomalyDetector:
    def __init__(self, window_size: int = 100, contamination: float = 0.05):
        self.window_size = window_size
        self.contamination = contamination
        self.buffer: deque[list[float]] = deque(maxlen=window_size)
        self.model = None
        self._trained = False

        if HAS_SKLEARN:
            self.model = IsolationForest(
                contamination=contamination,
                n_estimators=100,
                random_state=42,
            )

    def _extract_features(self, telemetry: dict) -> list[float]:
        """Extrae vector de features de la telemetría."""
        features = []
        for metric in FEATURE_ORDER:
            value = telemetry.get(metric, 0)
            if isinstance(value, (int, float)):
                features.append(float(value))
            else:
                features.append(0.0)
        return features

    def _train_if_ready(self):
        """Entrena el modelo cuando hay suficientes datos."""
        if not HAS_SKLEARN or self._trained:
            return
        if len(self.buffer) >= self.window_size // 2:
            X = np.array(list(self.buffer))
            self.model.fit(X)
            self._trained = True
            logger.info(
                f"Anomaly Detector entrenado con {len(self.buffer)} muestras"
            )

    def evaluate(self, telemetry: dict) -> dict:
        """
        Evalúa si la telemetría actual es anómala.
        Retorna: {"is_anomaly": bool, "score": float, "features": list[str]}
        """
        features = self._extract_features(telemetry)
        self.buffer.append(features)

        # Intentar entrenar si no está listo
        if not self._trained:
            self._train_if_ready()

        # Detección con Isolation Forest
        if HAS_SKLEARN and self._trained:
            return self._evaluate_ml(features, telemetry)

        # Fallback: detección por umbrales
        return self._evaluate_threshold(telemetry)

    def _evaluate_ml(self, features: list[float], telemetry: dict) -> dict:
        """Evaluación usando Isolation Forest."""
        X = np.array(features).reshape(1, -1)
        prediction = self.model.predict(X)[0]
        score = -self.model.score_samples(X)[0]  # Mayor = más anómalo

        # Normalizar score a 0-1
        score = min(max(score, 0), 1)

        anomalous_features = []
        if prediction == -1:
            # Identificar qué features contribuyen
            for i, metric in enumerate(FEATURE_ORDER):
                value = features[i]
                bounds = MONITORED_METRICS[metric]
                if value < bounds["min"] or value > bounds["max"]:
                    anomalous_features.append(metric)

        return {
            "is_anomaly": prediction == -1,
            "score": round(score, 3),
            "features": anomalous_features,
            "method": "isolation_forest",
        }

    def _evaluate_threshold(self, telemetry: dict) -> dict:
        """Evaluación por umbrales (fallback sin sklearn)."""
        anomalous = []
        for metric, bounds in MONITORED_METRICS.items():
            value = telemetry.get(metric)
            if value is None or not isinstance(value, (int, float)):
                continue
            # Solo considerar anómalo si la bomba está activa (pump_pressure > 0)
            # o si es una métrica que siempre aplica
            if metric == "pump_pressure" and value == 0:
                continue
            if value < bounds["min"] or value > bounds["max"]:
                anomalous.append(metric)

        score = len(anomalous) / len(MONITORED_METRICS) if anomalous else 0
        return {
            "is_anomaly": len(anomalous) > 0,
            "score": round(score, 3),
            "features": anomalous,
            "method": "threshold",
        }
