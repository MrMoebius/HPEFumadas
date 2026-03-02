"""
Estado compartido de la API.
Se suscribe a MQTT para mantener una copia del estado del vehículo en memoria,
y lee SQLite para datos históricos.
"""

import json
import os
import sqlite3
import threading
from collections import deque
from datetime import datetime

import paho.mqtt.client as mqtt
from loguru import logger
from config.settings import (
    MQTT_HOST, MQTT_PORT, TOPIC_TELEMETRY, TOPIC_ALERTS, TOPIC_ROUTE, VEHICLE_ID,
)

DB_PATH = os.getenv("DB_PATH", "/app/data/bomberos.db")


class SharedState:
    def __init__(self):
        self.vehicle_id = VEHICLE_ID
        self.current_state: dict = {}
        self.state_history: deque[dict] = deque(maxlen=500)
        self.active_alerts: list[dict] = []
        self.active_routes: dict[str, dict] = {}  # vehicle_id → route data
        self.mqtt_connected = False
        self._lock = threading.Lock()

        self.client = mqtt.Client(client_id=f"api-{VEHICLE_ID}")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(TOPIC_TELEMETRY, qos=1)
            client.subscribe(TOPIC_ALERTS, qos=1)
            client.subscribe(TOPIC_ROUTE, qos=1)
            self.mqtt_connected = True
            logger.info(f"API suscrita a MQTT ({TOPIC_TELEMETRY}, {TOPIC_ROUTE})")
        else:
            logger.error(f"Error MQTT: rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        self.mqtt_connected = False
        logger.warning("API desconectada de MQTT")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            with self._lock:
                if TOPIC_TELEMETRY in msg.topic:
                    self.current_state = payload
                    self.state_history.append(payload)
                elif "bomberos/ruta/" in msg.topic:
                    vid = msg.topic.split("/")[-1]
                    msg_type = payload.get("type", "")
                    if msg_type == "route_started":
                        self.active_routes[vid] = payload
                    elif msg_type == "route_completed":
                        self.active_routes.pop(vid, None)
                elif TOPIC_ALERTS in msg.topic:
                    self.active_alerts.append(payload)
        except Exception as e:
            logger.error(f"Error procesando mensaje MQTT: {e}")

    def start(self):
        self.client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

    def get_state(self) -> dict:
        with self._lock:
            return dict(self.current_state)

    def get_history(self, limit: int = 100) -> list[dict]:
        with self._lock:
            items = list(self.state_history)
            return items[-limit:]

    def get_route(self, vehicle_id: str) -> dict | None:
        with self._lock:
            return self.active_routes.get(vehicle_id)

    def get_alerts(self) -> list[dict]:
        with self._lock:
            return list(self.active_alerts)

    def get_alerts_from_db(self, limit: int = 50) -> list[dict]:
        """Lee alertas del SQLite compartido con twin-engine."""
        try:
            db = sqlite3.connect(DB_PATH)
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT * FROM alerts_history ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            db.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error leyendo alertas de SQLite: {e}")
            return []

    def get_telemetry_from_db(self, limit: int = 100) -> list[dict]:
        """Lee telemetría histórica del SQLite."""
        try:
            db = sqlite3.connect(DB_PATH)
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT * FROM telemetry_history ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            db.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error leyendo telemetría de SQLite: {e}")
            return []


shared_state = SharedState()
