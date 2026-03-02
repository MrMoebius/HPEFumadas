"""
Motor principal del Gemelo Digital — Camión de Bomberos BOM-001.
Orquesta todos los componentes: state manager, event processor, rule engine e IA.
"""

import sys
import os
import signal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loguru import logger
from core.state_manager import StateManager
from core.rule_engine import RuleEngine
from core.event_processor import EventProcessor
from ai.anomaly_detector import AnomalyDetector
from ai.failure_predictor import FailurePredictor
from ai.decision_assistant import DecisionAssistant
from config.settings import VEHICLE_ID


class TwinEngine:
    def __init__(self):
        logger.info(f"Inicializando Gemelo Digital para {VEHICLE_ID}...")

        # Componentes core
        self.state_manager = StateManager()
        self.rule_engine = RuleEngine()

        # Componentes IA
        self.anomaly_detector = AnomalyDetector()
        self.failure_predictor = FailurePredictor()
        self.decision_assistant = DecisionAssistant()

        # Procesador de eventos (conecta MQTT con todo lo demás)
        self.event_processor = EventProcessor(
            state_manager=self.state_manager,
            rule_engine=self.rule_engine,
            anomaly_detector=self.anomaly_detector,
            decision_assistant=self.decision_assistant,
        )

        logger.info("Todos los componentes inicializados")

    def run(self):
        """Inicia el motor del gemelo digital."""
        logger.info(f"=== Gemelo Digital {VEHICLE_ID} — ACTIVO ===")

        # Manejar señales de parada
        def handle_signal(sig, frame):
            logger.info("Señal de parada recibida, cerrando...")
            self.event_processor.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        # Iniciar escucha MQTT (bloqueante)
        self.event_processor.run()


def main():
    engine = TwinEngine()
    engine.run()


if __name__ == "__main__":
    main()
