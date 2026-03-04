"""
Gestiona el estado actual del vehículo y su histórico.
Recibe actualizaciones del Event Processor y las aplica al estado.
"""

import json
import os
import sqlite3
from datetime import datetime
from collections import deque
from threading import Lock

from loguru import logger
from core.models.vehicle import VehicleState
from core.models.alert import Alert

DB_PATH = os.getenv("DB_PATH", "/app/data/bomberos.db")


class StateManager:
    def __init__(self, max_history: int = 500):
        self.state = VehicleState()
        self.history: deque[dict] = deque(maxlen=max_history)
        self.alerts: list[Alert] = []
        self.alerts_history: list[Alert] = []
        self._lock = Lock()
        self._init_db()

    def _init_db(self):
        """Inicializa SQLite para persistencia."""
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id TEXT,
                timestamp TEXT,
                data JSON
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS alerts_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT,
                vehicle_id TEXT,
                timestamp TEXT,
                severity TEXT,
                original_severity TEXT DEFAULT '',
                category TEXT,
                message TEXT,
                metric TEXT,
                current_value REAL,
                threshold REAL,
                recommended_action TEXT,
                status TEXT DEFAULT 'activa',
                confirmed_by TEXT DEFAULT '',
                confirmed_at TEXT DEFAULT '',
                escalation_count INTEGER DEFAULT 0,
                history_json TEXT DEFAULT '[]'
            )
        """)
        # Migrar tabla existente si faltan columnas nuevas
        self._migrate_alerts_table()
        self.db.commit()
        logger.info(f"SQLite inicializado en {DB_PATH}")

    def _migrate_alerts_table(self):
        """Añade columnas nuevas a alerts_history si no existen."""
        cursor = self.db.execute("PRAGMA table_info(alerts_history)")
        existing = {row[1] for row in cursor.fetchall()}
        migrations = {
            "original_severity": "TEXT DEFAULT ''",
            "status": "TEXT DEFAULT 'activa'",
            "confirmed_by": "TEXT DEFAULT ''",
            "confirmed_at": "TEXT DEFAULT ''",
            "escalation_count": "INTEGER DEFAULT 0",
            "history_json": "TEXT DEFAULT '[]'",
        }
        for col, typedef in migrations.items():
            if col not in existing:
                try:
                    self.db.execute(f"ALTER TABLE alerts_history ADD COLUMN {col} {typedef}")
                except Exception:
                    pass

    def update(self, telemetry: dict):
        """Actualiza el estado con nueva telemetría."""
        with self._lock:
            for key, value in telemetry.items():
                if hasattr(self.state, key):
                    setattr(self.state, key, value)

            # Guardar en histórico en memoria
            snapshot = self.state.model_dump()
            snapshot["timestamp"] = str(snapshot["timestamp"])
            self.history.append(snapshot)

            # Persistir cada 10 ticks
            if self.state.tick % 10 == 0:
                self._persist_telemetry(snapshot)

    def _persist_telemetry(self, snapshot: dict):
        """Guarda snapshot en SQLite."""
        try:
            self.db.execute(
                "INSERT INTO telemetry_history (vehicle_id, timestamp, data) VALUES (?, ?, ?)",
                (snapshot["vehicle_id"], snapshot["timestamp"], json.dumps(snapshot)),
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Error persistiendo telemetría: {e}")

    def add_alert(self, alert: Alert):
        """Registra una nueva alerta."""
        with self._lock:
            # Evitar alertas duplicadas en ventana corta
            for existing in self.alerts:
                if existing.metric == alert.metric and existing.severity == alert.severity:
                    return

            self.alerts.append(alert)
            self.alerts_history.append(alert)

            # Actualizar anomalías en el estado
            if alert.metric not in self.state.anomalies:
                self.state.anomalies.append(alert.metric)

            # Persistir
            self._persist_alert(alert)
            logger.warning(
                f"ALERTA [{alert.severity}] {alert.category}: "
                f"{alert.message} ({alert.metric}={alert.current_value})"
            )

    def _persist_alert(self, alert: Alert):
        """Guarda alerta en SQLite."""
        try:
            self.db.execute(
                """INSERT INTO alerts_history
                   (alert_id, vehicle_id, timestamp, severity, original_severity,
                    category, message, metric, current_value, threshold,
                    recommended_action, status, confirmed_by, confirmed_at,
                    escalation_count, history_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    alert.alert_id, alert.vehicle_id, str(alert.timestamp),
                    alert.severity, alert.original_severity,
                    alert.category, alert.message,
                    alert.metric, alert.current_value, alert.threshold,
                    alert.recommended_action, alert.status,
                    alert.confirmed_by,
                    str(alert.confirmed_at) if alert.confirmed_at else "",
                    alert.escalation_count,
                    json.dumps(alert.history),
                ),
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Error persistiendo alerta: {e}")

    def _update_alert_in_db(self, alert: Alert):
        """Actualiza una alerta existente en SQLite."""
        try:
            self.db.execute(
                """UPDATE alerts_history SET
                    severity = ?, status = ?, confirmed_by = ?, confirmed_at = ?,
                    escalation_count = ?, history_json = ?
                   WHERE alert_id = ?""",
                (
                    alert.severity, alert.status, alert.confirmed_by,
                    str(alert.confirmed_at) if alert.confirmed_at else "",
                    alert.escalation_count, json.dumps(alert.history),
                    alert.alert_id,
                ),
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Error actualizando alerta en DB: {e}")

    def confirm_alert(self, alert_id: str, operator: str = "operador") -> Alert | None:
        """Confirma una alerta activa."""
        with self._lock:
            for alert in self.alerts:
                if alert.alert_id == alert_id:
                    alert.confirm(operator)
                    self._update_alert_in_db(alert)
                    logger.info(f"Alerta {alert_id} confirmada por {operator}")
                    return alert
        return None

    def dismiss_alert(self, alert_id: str, operator: str = "operador") -> Alert | None:
        """Descarta una alerta activa."""
        with self._lock:
            for alert in self.alerts:
                if alert.alert_id == alert_id:
                    alert.dismiss(operator)
                    self._update_alert_in_db(alert)
                    self.alerts = [a for a in self.alerts if a.alert_id != alert_id]
                    if alert.metric in self.state.anomalies:
                        self.state.anomalies.remove(alert.metric)
                    logger.info(f"Alerta {alert_id} descartada por {operator}")
                    return alert
        return None

    def escalate_alert(self, alert: Alert):
        """Persiste la escalación de una alerta."""
        self._update_alert_in_db(alert)

    def clear_alert(self, metric: str):
        """Limpia alertas resueltas para una métrica."""
        with self._lock:
            for alert in self.alerts:
                if alert.metric == metric:
                    alert.resolve()
                    self._update_alert_in_db(alert)
            self.alerts = [a for a in self.alerts if a.metric != metric]
            if metric in self.state.anomalies:
                self.state.anomalies.remove(metric)

    def get_state(self) -> dict:
        """Retorna el estado actual como dict."""
        with self._lock:
            return self.state.model_dump()

    def get_history(self, limit: int = 100) -> list[dict]:
        """Retorna los últimos N estados."""
        with self._lock:
            items = list(self.history)
            return items[-limit:]

    def get_alerts(self, active_only: bool = True) -> list[dict]:
        """Retorna alertas."""
        with self._lock:
            source = self.alerts if active_only else self.alerts_history
            return [a.model_dump() for a in source]

    def update_risk_score(self, score: float):
        """Actualiza el score de riesgo."""
        with self._lock:
            self.state.risk_score = round(min(max(score, 0.0), 1.0), 3)
