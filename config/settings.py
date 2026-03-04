import os
from dotenv import load_dotenv

load_dotenv()

# MQTT
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

# InfluxDB
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "token-bomberos-dev")
INFLUX_ORG = os.getenv("INFLUX_ORG", "bomberos")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "telemetria")

# Vehículo
VEHICLE_ID = os.getenv("VEHICLE_ID", "BOM-001")
TICK_INTERVAL = int(os.getenv("TICK_INTERVAL", 2))

# API
API_PORT = int(os.getenv("API_PORT", 8000))
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Dashboard
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", 8501))

# MQTT Topics
TOPIC_TELEMETRY = f"bomberos/telemetria/{VEHICLE_ID}"
TOPIC_ALERTS = f"bomberos/alertas/{VEHICLE_ID}"
TOPIC_COMMANDS = f"bomberos/comandos/{VEHICLE_ID}"
TOPIC_STATUS = f"bomberos/estado/{VEHICLE_ID}"
TOPIC_ROUTE = f"bomberos/ruta/{VEHICLE_ID}"
TOPIC_CHAT = f"bomberos/chat/{VEHICLE_ID}"
