"""
RouteSimulator — movimiento tick-a-tick interpolado por coordenadas de ruta real.
En cada tick avanza una distancia proporcional a la velocidad actual.
"""

import math
from geo.engine import _haversine_m


class RouteSimulator:
    """Simula el avance del vehículo sobre una ruta de coordenadas reales."""

    def __init__(self, coords: list[tuple], speed_kmh: float = 60.0):
        """
        coords: lista de (lat, lon) que forman la ruta.
        speed_kmh: velocidad media de desplazamiento.
        """
        self.coords = list(coords)
        self.speed_kmh = speed_kmh

        # Precalcular distancias acumuladas por segmento
        self._seg_distances = []  # distancia de cada segmento en metros
        self._cumulative = [0.0]  # distancia acumulada hasta cada punto
        for i in range(len(self.coords) - 1):
            d = _haversine_m(self.coords[i], self.coords[i + 1])
            self._seg_distances.append(d)
            self._cumulative.append(self._cumulative[-1] + d)

        self.total_distance_m = self._cumulative[-1] if self._cumulative else 0.0
        self._distance_traveled = 0.0  # metros recorridos

    @property
    def progress(self) -> float:
        """Progreso de 0.0 a 1.0."""
        if self.total_distance_m <= 0:
            return 1.0
        return min(self._distance_traveled / self.total_distance_m, 1.0)

    @property
    def distance_remaining_m(self) -> float:
        return max(0.0, self.total_distance_m - self._distance_traveled)

    @property
    def finished(self) -> bool:
        return self._distance_traveled >= self.total_distance_m

    def eta_seconds(self, congestion_factor: float = 1.0) -> float:
        """ETA en segundos considerando velocidad actual y congestión."""
        if self.speed_kmh <= 0:
            return 0.0
        speed_ms = (self.speed_kmh / 3.6) / congestion_factor
        if speed_ms <= 0:
            return 0.0
        return self.distance_remaining_m / speed_ms

    def current_position(self) -> tuple:
        """Retorna la posición (lat, lon) interpolada actual."""
        if not self.coords:
            return (0.0, 0.0)
        if self.finished:
            return self.coords[-1]

        # Encontrar el segmento actual
        for i in range(len(self._cumulative) - 1):
            if self._distance_traveled <= self._cumulative[i + 1]:
                seg_start = self._cumulative[i]
                seg_len = self._seg_distances[i]
                if seg_len <= 0:
                    return self.coords[i]
                t = (self._distance_traveled - seg_start) / seg_len
                lat = self.coords[i][0] + t * (self.coords[i + 1][0] - self.coords[i][0])
                lon = self.coords[i][1] + t * (self.coords[i + 1][1] - self.coords[i][1])
                return (lat, lon)

        return self.coords[-1]

    def heading(self) -> float:
        """Heading actual en grados (0=N, 90=E)."""
        if not self.coords or self.finished:
            return 0.0

        for i in range(len(self._cumulative) - 1):
            if self._distance_traveled <= self._cumulative[i + 1]:
                dlat = self.coords[i + 1][0] - self.coords[i][0]
                dlon = self.coords[i + 1][1] - self.coords[i][1]
                return (math.degrees(math.atan2(dlon, dlat)) + 360) % 360

        return 0.0

    def tick(self, dt_seconds: float, speed_kmh: float,
             congestion_factor: float = 1.0) -> tuple:
        """
        Avanza el vehículo un tick.
        Retorna (lat, lon) de la nueva posición.
        """
        self.speed_kmh = speed_kmh
        effective_speed = speed_kmh / congestion_factor
        distance_m = (effective_speed / 3.6) * dt_seconds
        self._distance_traveled = min(
            self._distance_traveled + distance_m,
            self.total_distance_m,
        )
        return self.current_position()
