"""
GeoEngine — Carga grafo OSM de Valencia, calcula rutas reales por calles.
Usa cache en disco (.graphml) para evitar descargar el grafo cada vez.
"""

import os
import math
from loguru import logger

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
GRAPHML_PATH = os.path.join(CACHE_DIR, "valencia_drive.graphml")

# Bounding box de Valencia centro (approx.)
VALENCIA_CENTER = (39.4699, -0.3763)
VALENCIA_DIST_M = 8000  # radio en metros para descargar el grafo


class GeoEngine:
    """Motor de cartografía basado en OSM + osmnx + networkx."""

    def __init__(self):
        self.graph = None
        self._graph_undirected = None
        self.available = False
        self._ox = None
        self._nx = None
        self._has_travel_times = False
        self._load()

    def _load(self):
        """Intenta cargar el grafo OSM, primero desde cache, luego descargando."""
        try:
            import osmnx as ox
            import networkx as nx
            self._ox = ox
            self._nx = nx
        except ImportError:
            logger.warning("osmnx/networkx no disponibles — GeoEngine desactivado")
            return

        os.makedirs(CACHE_DIR, exist_ok=True)

        # Intentar cargar desde cache
        if os.path.exists(GRAPHML_PATH):
            try:
                self.graph = self._ox.load_graphml(GRAPHML_PATH)
                self._graph_undirected = self.graph.to_undirected()
                self.available = True
                logger.info(
                    f"GeoEngine loaded (cache): "
                    f"{self.graph.number_of_nodes()} nodos, "
                    f"{self.graph.number_of_edges()} aristas"
                )
                return
            except Exception as e:
                logger.warning(f"Error leyendo cache graphml: {e}")

        # Descargar el grafo desde OSM
        try:
            logger.info(
                "Descargando grafo OSM de Valencia "
                f"(radio {VALENCIA_DIST_M}m)... puede tardar 30-60s"
            )
            self.graph = self._ox.graph_from_point(
                VALENCIA_CENTER, dist=VALENCIA_DIST_M,
                network_type="drive", simplify=True,
            )
            self._ox.save_graphml(self.graph, GRAPHML_PATH)
            self._graph_undirected = self.graph.to_undirected()
            self.available = True
            logger.info(
                f"GeoEngine loaded (descargado): "
                f"{self.graph.number_of_nodes()} nodos, "
                f"{self.graph.number_of_edges()} aristas"
            )
        except Exception as e:
            logger.error(f"No se pudo descargar grafo OSM: {e}")
            logger.warning("GeoEngine NO disponible — se usará fallback de waypoints")

    def shortest_route(self, origin: tuple, destination: tuple) -> list[tuple]:
        """
        Calcula la ruta más corta entre dos coordenadas (lat, lon).
        Retorna lista de (lat, lon) representando la ruta por calles reales.
        Primero intenta grafo dirigido, si falla usa no-dirigido (ignora sentidos).
        Retorna lista vacía si no se puede calcular.
        """
        if not self.available:
            return []

        try:
            orig_node = self._ox.nearest_nodes(
                self.graph, X=origin[1], Y=origin[0]
            )
            dest_node = self._ox.nearest_nodes(
                self.graph, X=destination[1], Y=destination[0]
            )

            # Intentar ruta en grafo dirigido (respeta sentidos)
            try:
                route_nodes = self._nx.shortest_path(
                    self.graph, orig_node, dest_node, weight="length"
                )
            except self._nx.NetworkXNoPath:
                # Fallback a grafo no-dirigido (ignora sentidos, pero sigue calles)
                logger.debug("Sin ruta dirigida, usando grafo no-dirigido")
                route_nodes = self._nx.shortest_path(
                    self._graph_undirected, orig_node, dest_node, weight="length"
                )

            coords = []
            for node in route_nodes:
                data = self.graph.nodes[node]
                coords.append((data["y"], data["x"]))

            return coords

        except Exception as e:
            logger.error(f"Error calculando ruta: {e}")
            return []

    def _ensure_travel_times(self):
        """Añade speed_kph y travel_time a las aristas si no existen."""
        if self._has_travel_times:
            return
        try:
            self._ox.add_edge_speeds(self.graph)
            self._ox.add_edge_travel_times(self.graph)
            # También al grafo no-dirigido
            if self._graph_undirected is not None:
                try:
                    self._ox.add_edge_speeds(self._graph_undirected)
                    self._ox.add_edge_travel_times(self._graph_undirected)
                except Exception:
                    for _, _, data in self._graph_undirected.edges(data=True):
                        length = data.get("length", 100)
                        data["travel_time"] = length / 11.1
            self._has_travel_times = True
            logger.info("Travel times añadidos al grafo")
        except Exception as e:
            logger.warning(f"osmnx add_edge_speeds falló: {e} — usando fallback 40km/h")
            for _, _, data in self.graph.edges(data=True):
                length = data.get("length", 100)
                data["travel_time"] = length / 11.1
            if self._graph_undirected is not None:
                for _, _, data in self._graph_undirected.edges(data=True):
                    length = data.get("length", 100)
                    data["travel_time"] = length / 11.1
            self._has_travel_times = True

    def fastest_route(
        self, origin: tuple, destination: tuple, traffic_zones: list[dict],
    ) -> list[tuple]:
        """
        Calcula la ruta más rápida evitando zonas congestionadas.
        traffic_zones: lista de dicts con lat, lon, radius, congestion_factor.
        Retorna lista de (lat, lon). Lista vacía si falla.
        """
        if not self.available:
            return []

        try:
            self._ensure_travel_times()

            orig_node = self._ox.nearest_nodes(
                self.graph, X=origin[1], Y=origin[0]
            )
            dest_node = self._ox.nearest_nodes(
                self.graph, X=destination[1], Y=destination[0]
            )

            # Pre-computar congestión por nodo
            node_congestion = {}
            for node, ndata in self.graph.nodes(data=True):
                nlat, nlon = ndata["y"], ndata["x"]
                max_cong = 1.0
                for z in traffic_zones:
                    dlat = (nlat - z["lat"]) * 111000
                    dlon = (nlon - z["lon"]) * 85000
                    dist_m = (dlat**2 + dlon**2) ** 0.5
                    if dist_m < z.get("radius", 200):
                        max_cong = max(max_cong, z.get("congestion_factor", 1.0))
                if max_cong > 1.0:
                    node_congestion[node] = max_cong

            # traffic_time = travel_time * congestión en cada arista
            for u, v, data in self.graph.edges(data=True):
                base = data.get("travel_time", data.get("length", 100) / 11.1)
                cong = max(
                    node_congestion.get(u, 1.0),
                    node_congestion.get(v, 1.0),
                )
                data["traffic_time"] = base * cong

            try:
                route_nodes = self._nx.shortest_path(
                    self.graph, orig_node, dest_node, weight="traffic_time"
                )
            except self._nx.NetworkXNoPath:
                logger.debug("Sin ruta dirigida (traffic), usando no-dirigido")
                for u, v, data in self._graph_undirected.edges(data=True):
                    base = data.get("travel_time", data.get("length", 100) / 11.1)
                    cong = max(
                        node_congestion.get(u, 1.0),
                        node_congestion.get(v, 1.0),
                    )
                    data["traffic_time"] = base * cong
                route_nodes = self._nx.shortest_path(
                    self._graph_undirected, orig_node, dest_node,
                    weight="traffic_time",
                )

            coords = []
            for node in route_nodes:
                data = self.graph.nodes[node]
                coords.append((data["y"], data["x"]))

            return coords

        except Exception as e:
            logger.error(f"Error calculando ruta rápida: {e}")
            return []

    def route_distance_m(self, coords: list[tuple]) -> float:
        """Calcula distancia total de una ruta en metros (Haversine)."""
        total = 0.0
        for i in range(len(coords) - 1):
            total += _haversine_m(coords[i], coords[i + 1])
        return total


def _haversine_m(p1: tuple, p2: tuple) -> float:
    """Distancia Haversine entre dos puntos (lat, lon) en metros."""
    R = 6_371_000
    lat1, lon1 = math.radians(p1[0]), math.radians(p1[1])
    lat2, lon2 = math.radians(p2[0]), math.radians(p2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
