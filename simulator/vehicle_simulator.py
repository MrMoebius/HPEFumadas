"""
Simulador de telemetría del camión de bomberos BOM-001.
Genera datos realistas y los publica en MQTT cada TICK_INTERVAL segundos.
"""

import json
import math
import random
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import paho.mqtt.client as mqtt
from loguru import logger
from config.settings import (
    MQTT_HOST, MQTT_PORT, VEHICLE_ID, TICK_INTERVAL,
    TOPIC_TELEMETRY, TOPIC_STATUS,
)
from simulator.mission_simulator import MissionSimulator


class VehicleSimulator:
    def __init__(self):
        self.vehicle_id = VEHICLE_ID
        self.vehicle_type = "camion_bomberos_BUP"
        self.mission = MissionSimulator()
        self.tick = 0

        # Motor y mecánica
        self.engine_temp = 85.0
        self.engine_rpm = 800
        self.fuel_level = 95.0
        self.oil_pressure = 40.0
        self.battery_voltage = 13.2
        self.brake_wear = 15.0
        self.tire_pressure = {"FL": 35.0, "FR": 35.0, "RL": 33.0, "RR": 33.0}
        self.mileage_km = 42350.0

        # Ubicación (estación de bomberos Valencia — Plaza del Ayuntamiento)
        self.latitude = 39.4699
        self.longitude = -0.3763
        self.speed_kmh = 0.0
        self.heading = 0.0

        # Equipamiento contra incendios
        self.water_tank_level = 100.0
        self.foam_tank_level = 100.0
        self.pump_pressure = 0.0
        self.ladder_status = "retracted"
        self.ladder_angle = 0.0
        self.hose_deployed = False
        self.hydraulic_pressure = 150.0
        self.crew_count = 6

        # Misión
        self.mission_status = "disponible"
        self.sirens_active = False
        self.lights_active = False

        # MQTT
        self.client = mqtt.Client(client_id=f"sim-{self.vehicle_id}")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

        # Ruta actual (lista de waypoints)
        self._route = []
        self._route_index = 0

        # Cargar rutas
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        with open(os.path.join(data_dir, "routes.json"), "r") as f:
            self._routes_data = json.load(f)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Conectado a MQTT broker ({MQTT_HOST}:{MQTT_PORT})")
        else:
            logger.error(f"Error de conexión MQTT: rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        logger.warning(f"Desconectado de MQTT (rc={rc})")

    def connect(self):
        logger.info(f"Conectando a {MQTT_HOST}:{MQTT_PORT}...")
        self.client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        self.client.loop_start()

    def _simulate_engine(self):
        """Simula parámetros del motor según estado de misión."""
        if self.mission_status == "disponible":
            target_rpm = 800
            target_temp = 85.0
        elif self.mission_status == "en_ruta":
            target_rpm = random.randint(2500, 3500)
            target_temp = 95.0 + random.uniform(0, 10)
        elif self.mission_status == "en_escena":
            target_rpm = random.randint(1800, 2500)
            target_temp = 100.0 + random.uniform(0, 15)
        else:  # regreso_base
            target_rpm = random.randint(1500, 2500)
            target_temp = 90.0 + random.uniform(0, 5)

        # Transición suave
        self.engine_rpm += int((target_rpm - self.engine_rpm) * 0.3)
        self.engine_temp += (target_temp - self.engine_temp) * 0.1
        self.engine_temp += random.uniform(-0.5, 0.5)

        # Consumo de combustible
        if self.mission_status != "disponible":
            consumption = 0.02 + (self.engine_rpm / 3500) * 0.08
            if self.mission_status == "en_escena":
                consumption += 0.05  # Bomba de agua consume más
            self.fuel_level = max(0, self.fuel_level - consumption)

        # Aceite y batería
        self.oil_pressure = 35.0 + (self.engine_rpm / 3500) * 20.0 + random.uniform(-2, 2)
        self.battery_voltage = 13.2 + random.uniform(-0.3, 0.3)
        if self.mission_status == "en_escena":
            self.battery_voltage -= 0.5  # Más carga eléctrica

        # Desgaste de frenos (muy lento)
        if self.mission_status in ("en_ruta", "regreso_base"):
            self.brake_wear += random.uniform(0, 0.005)

        # Presión de neumáticos (pequeñas variaciones)
        for tire in self.tire_pressure:
            self.tire_pressure[tire] += random.uniform(-0.05, 0.05)

        # Kilometraje
        if self.speed_kmh > 0:
            self.mileage_km += (self.speed_kmh / 3600) * TICK_INTERVAL

    def _simulate_movement(self):
        """Simula movimiento GPS siguiendo una ruta."""
        if self.mission_status == "disponible":
            self.speed_kmh = 0.0
            return

        if self.mission_status in ("en_ruta", "regreso_base"):
            if self._route and self._route_index < len(self._route):
                target = self._route[self._route_index]
                dlat = target["lat"] - self.latitude
                dlon = target["lon"] - self.longitude
                dist = math.sqrt(dlat**2 + dlon**2)

                if dist < 0.0003:  # ~30m, llegó al waypoint
                    self._route_index += 1
                else:
                    # Velocidad según misión
                    if self.mission_status == "en_ruta":
                        self.speed_kmh = random.uniform(50, 80)
                    else:
                        self.speed_kmh = random.uniform(30, 50)

                    # Mover hacia el waypoint
                    step = (self.speed_kmh / 3600) * TICK_INTERVAL / 111000
                    ratio = min(step / dist, 1.0)
                    self.latitude += dlat * ratio
                    self.longitude += dlon * ratio

                    # Heading
                    self.heading = (math.degrees(math.atan2(dlon, dlat)) + 360) % 360
            else:
                self.speed_kmh = 0.0

        elif self.mission_status == "en_escena":
            self.speed_kmh = 0.0

    def _simulate_firefighting(self):
        """Simula equipamiento contra incendios según estado de misión."""
        if self.mission_status == "en_escena":
            # Activar equipamiento
            if not self.hose_deployed:
                self.hose_deployed = True
                self.pump_pressure = 120.0 + random.uniform(0, 30)
                logger.info("Manguera desplegada, bomba activada")

            # Consumo de agua
            self.water_tank_level = max(0, self.water_tank_level - random.uniform(0.3, 0.8))
            # Consumo de espuma (menor)
            self.foam_tank_level = max(0, self.foam_tank_level - random.uniform(0.05, 0.15))
            # Presión de bomba con variaciones
            self.pump_pressure = 120.0 + random.uniform(-10, 15)

            # Escalera (desplegar si es incendio en edificio)
            if self.ladder_status == "retracted" and random.random() < 0.02:
                self.ladder_status = "extended"
                self.ladder_angle = random.uniform(30, 65)
                logger.info(f"Escalera extendida a {self.ladder_angle:.1f}°")

            # Presión hidráulica varía
            if self.ladder_status == "extended":
                self.hydraulic_pressure = 140.0 + random.uniform(-15, 10)
            else:
                self.hydraulic_pressure = 150.0 + random.uniform(-5, 5)

        elif self.mission_status == "disponible":
            # Recargar al volver a base
            self.water_tank_level = min(100, self.water_tank_level + 2.0)
            self.foam_tank_level = min(100, self.foam_tank_level + 1.0)
            self.pump_pressure = 0.0
            self.hose_deployed = False
            if self.ladder_status == "extended":
                self.ladder_status = "retracted"
                self.ladder_angle = 0.0
            self.hydraulic_pressure = 150.0 + random.uniform(-3, 3)

        elif self.mission_status in ("en_ruta", "regreso_base"):
            self.pump_pressure = 0.0
            self.hose_deployed = False
            self.hydraulic_pressure = 150.0 + random.uniform(-3, 3)

    def _simulate_mission(self):
        """Delega la lógica de misión al MissionSimulator."""
        prev_status = self.mission_status
        self.mission_status = self.mission.update(
            self.mission_status,
            self._route_index,
            len(self._route),
            self.water_tank_level,
            self.tick,
        )

        if self.mission_status != prev_status:
            logger.info(f"Misión: {prev_status} → {self.mission_status}")

            if self.mission_status == "en_ruta":
                # Seleccionar ruta aleatoria
                route_name = random.choice(list(self._routes_data.keys()))
                self._route = self._routes_data[route_name]["waypoints"]
                self._route_index = 0
                self.sirens_active = True
                self.lights_active = True
                logger.info(f"Despachado a: {route_name}")

            elif self.mission_status == "en_escena":
                self.sirens_active = False

            elif self.mission_status == "regreso_base":
                # Ruta inversa a la base
                base = self._routes_data[list(self._routes_data.keys())[0]]["waypoints"][0]
                self._route = [base]
                self._route_index = 0
                self.sirens_active = False
                self.lights_active = True

            elif self.mission_status == "disponible":
                self.sirens_active = False
                self.lights_active = False
                self._route = []
                self._route_index = 0

    def get_state(self) -> dict:
        """Retorna el estado completo del vehículo como dict."""
        return {
            "vehicle_id": self.vehicle_id,
            "vehicle_type": self.vehicle_type,
            "engine_temp": round(self.engine_temp, 1),
            "engine_rpm": self.engine_rpm,
            "fuel_level": round(self.fuel_level, 1),
            "oil_pressure": round(self.oil_pressure, 1),
            "battery_voltage": round(self.battery_voltage, 2),
            "brake_wear": round(self.brake_wear, 1),
            "tire_pressure": {k: round(v, 1) for k, v in self.tire_pressure.items()},
            "mileage_km": round(self.mileage_km, 1),
            "latitude": round(self.latitude, 6),
            "longitude": round(self.longitude, 6),
            "speed_kmh": round(self.speed_kmh, 1),
            "heading": round(self.heading, 1),
            "water_tank_level": round(self.water_tank_level, 1),
            "foam_tank_level": round(self.foam_tank_level, 1),
            "pump_pressure": round(self.pump_pressure, 1),
            "ladder_status": self.ladder_status,
            "ladder_angle": round(self.ladder_angle, 1),
            "hose_deployed": self.hose_deployed,
            "hydraulic_pressure": round(self.hydraulic_pressure, 1),
            "crew_count": self.crew_count,
            "mission_status": self.mission_status,
            "sirens_active": self.sirens_active,
            "lights_active": self.lights_active,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tick": self.tick,
        }

    def publish_state(self):
        """Publica el estado completo en MQTT."""
        state = self.get_state()
        payload = json.dumps(state)
        self.client.publish(TOPIC_TELEMETRY, payload, qos=1)
        self.client.publish(TOPIC_STATUS, json.dumps({
            "vehicle_id": self.vehicle_id,
            "mission_status": self.mission_status,
            "timestamp": state["timestamp"],
        }), qos=0)

    def step(self):
        """Ejecuta un tick de simulación."""
        self._simulate_mission()
        self._simulate_engine()
        self._simulate_movement()
        self._simulate_firefighting()
        self.publish_state()
        self.tick += 1

    def run(self):
        """Bucle principal de simulación."""
        self.connect()
        time.sleep(1)  # Esperar conexión MQTT
        logger.info(f"Simulador {self.vehicle_id} iniciado (tick={TICK_INTERVAL}s)")

        try:
            while True:
                self.step()
                state = self.get_state()
                logger.debug(
                    f"[{state['timestamp']}] {self.mission_status} | "
                    f"vel={self.speed_kmh:.0f}km/h | "
                    f"motor={self.engine_temp:.0f}°C | "
                    f"agua={self.water_tank_level:.0f}% | "
                    f"bomba={self.pump_pressure:.0f}PSI"
                )
                time.sleep(TICK_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Simulador detenido")
        finally:
            self.client.loop_stop()
            self.client.disconnect()


if __name__ == "__main__":
    sim = VehicleSimulator()
    sim.run()
