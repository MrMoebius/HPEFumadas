"""
Simulador de misiones del camión de bomberos.
Gestiona las transiciones de estado del ciclo de misión:
disponible → en_ruta → en_escena → regreso_base → disponible
"""

import random
from loguru import logger


class MissionSimulator:
    def __init__(self):
        self.scene_ticks = 0
        self.scene_duration = 0
        self.cooldown_ticks = 0
        self.cooldown_duration = 0

    def update(
        self,
        current_status: str,
        route_index: int,
        route_length: int,
        water_level: float,
        tick: int,
    ) -> str:
        """
        Calcula el siguiente estado de la misión.
        Retorna el nuevo mission_status.
        """

        if current_status == "disponible":
            # Probabilidad de recibir una emergencia (~cada 30-60 ticks)
            self.cooldown_ticks += 1
            if self.cooldown_ticks >= self.cooldown_duration:
                if random.random() < 0.05:
                    self.scene_ticks = 0
                    self.scene_duration = random.randint(25, 60)
                    logger.info(
                        f"¡EMERGENCIA! Duración estimada en escena: "
                        f"{self.scene_duration * 2}s"
                    )
                    return "en_ruta"
            return "disponible"

        elif current_status == "en_ruta":
            # Llegó al destino (recorrió toda la ruta)
            if route_length > 0 and route_index >= route_length:
                self.scene_ticks = 0
                return "en_escena"
            return "en_ruta"

        elif current_status == "en_escena":
            self.scene_ticks += 1
            # Terminar si se acabó el tiempo o el agua
            if self.scene_ticks >= self.scene_duration or water_level <= 5.0:
                if water_level <= 5.0:
                    logger.warning("¡Agua agotada! Retirándose de la escena")
                else:
                    logger.info("Incendio controlado. Regresando a base")
                return "regreso_base"
            return "en_escena"

        elif current_status == "regreso_base":
            # Llegó a base (recorrió la ruta de vuelta)
            if route_length > 0 and route_index >= route_length:
                self.cooldown_ticks = 0
                self.cooldown_duration = random.randint(15, 40)
                logger.info(
                    f"En base. Cooldown: {self.cooldown_duration * 2}s"
                )
                return "disponible"
            return "regreso_base"

        return current_status
