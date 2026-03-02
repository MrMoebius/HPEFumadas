"""
Consume mensajes MQTT del simulador, parsea la telemetría
y distribuye a State Manager, Rule Engine y módulos de IA.
"""

import json
import paho.mqtt.client as mqtt
from loguru import logger
from config.settings import MQTT_HOST, MQTT_PORT, TOPIC_TELEMETRY, VEHICLE_ID


class EventProcessor:
    def __init__(self, state_manager, rule_engine, anomaly_detector, decision_assistant):
        self.state_manager = state_manager
        self.rule_engine = rule_engine
        self.anomaly_detector = anomaly_detector
        self.decision_assistant = decision_assistant

        self.client = mqtt.Client(client_id=f"twin-{VEHICLE_ID}")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        self._tick_count = 0

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            # Suscribirse a telemetría del vehículo
            client.subscribe(f"{TOPIC_TELEMETRY}", qos=1)
            logger.info(f"Twin-engine suscrito a {TOPIC_TELEMETRY}")
        else:
            logger.error(f"Error conectando a MQTT: rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        logger.warning(f"Twin-engine desconectado de MQTT (rc={rc})")

    def _on_message(self, client, userdata, msg):
        """Procesa cada mensaje de telemetría recibido."""
        try:
            payload = json.loads(msg.payload.decode())
            self._process_telemetry(payload)
        except json.JSONDecodeError:
            logger.error(f"Mensaje MQTT inválido: {msg.payload[:100]}")
        except Exception as e:
            logger.error(f"Error procesando telemetría: {e}")

    def _process_telemetry(self, telemetry: dict):
        """Pipeline de procesamiento de telemetría."""
        # 1. Actualizar estado
        self.state_manager.update(telemetry)
        self._tick_count += 1

        # 2. Evaluar reglas (cada tick)
        alerts = self.rule_engine.evaluate(telemetry)
        for alert in alerts:
            self.state_manager.add_alert(alert)

        # 3. Detección de anomalías (cada 5 ticks para no sobrecargar)
        if self._tick_count % 5 == 0:
            anomaly_result = self.anomaly_detector.evaluate(telemetry)
            if anomaly_result["is_anomaly"]:
                logger.warning(
                    f"Anomalía detectada: score={anomaly_result['score']:.2f} "
                    f"features={anomaly_result['features']}"
                )
                # Actualizar risk_score basado en anomalías
                risk = anomaly_result["score"] * 0.7 + len(self.state_manager.alerts) * 0.1
                self.state_manager.update_risk_score(risk)

        # 4. Asistente de decisiones (cada 5 ticks)
        if self._tick_count % 5 == 0:
            decisions = self.decision_assistant.evaluate(telemetry)
            for decision in decisions:
                logger.info(f"DECISIÓN: {decision}")

        # 5. Limpiar alertas resueltas
        self._check_resolved_alerts(telemetry)

    def _check_resolved_alerts(self, telemetry: dict):
        """Limpia alertas cuya métrica volvió a rango normal."""
        thresholds = {
            "engine_temp": lambda v: v < 100,
            "pump_pressure": lambda v: v > 80 or v == 0,
            "water_tank_level": lambda v: v > 20,
            "foam_tank_level": lambda v: v > 25,
            "hydraulic_pressure": lambda v: v > 100,
            "battery_voltage": lambda v: v > 12.0,
        }
        for metric, is_normal in thresholds.items():
            if metric in telemetry and is_normal(telemetry[metric]):
                self.state_manager.clear_alert(metric)

    def connect(self):
        """Conecta al broker MQTT."""
        logger.info(f"Twin-engine conectando a {MQTT_HOST}:{MQTT_PORT}...")
        self.client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)

    def run(self):
        """Inicia el loop de escucha MQTT (bloqueante)."""
        self.connect()
        logger.info("Twin-engine escuchando telemetría...")
        self.client.loop_forever()

    def stop(self):
        """Detiene el procesador."""
        self.client.loop_stop()
        self.client.disconnect()
