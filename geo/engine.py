"""
GeoEngine — Carga grafos OSM de multiples ciudades, calcula rutas reales por calles.
Usa cache en disco (.graphml) para evitar descargar el grafo cada vez.
Carga lazy: solo se descarga el grafo de una ciudad cuando se solicita.
"""

import os
import math
from loguru import logger

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")

# Configuracion por ciudad: centro y radio de descarga
CITY_CONFIGS = {
    "Valencia": {"center": (39.4699, -0.3763), "dist_m": 8000},
    "Madrid": {"center": (40.4168, -3.7038), "dist_m": 10000},
    "Barcelona": {"center": (41.3874, 2.1686), "dist_m": 10000},
    "Sevilla": {"center": (37.3891, -5.9845), "dist_m": 8000},
    "Bilbao": {"center": (43.2630, -2.9350), "dist_m": 7000},
}

DEFAULT_CITY = "Valencia"


class GeoEngine:
    """Motor de cartografia basado en OSM + osmnx + networkx. Soporte multi-ciudad."""

    def __init__(self):
        self._graphs = {}           # city -> grafo dirigido
        self._graphs_undirected = {}  # city -> grafo no-dirigido
        self._travel_times = set()  # ciudades con travel_time ya calculado
        self._active_city = DEFAULT_CITY
        self.available = False
        self._ox = None
        self._nx = None
        self._load_libs()
        # Cargar Valencia al inicio (como antes)
        if self._ox is not None:
            self.load_city(DEFAULT_CITY)

    @property
    def graph(self):
        """Grafo de la ciudad activa (compatibilidad)."""
        return self._graphs.get(self._active_city)

    @property
    def _graph_undirected(self):
        """Grafo no-dirigido de la ciudad activa (compatibilidad)."""
        return self._graphs_undirected.get(self._active_city)

    def _load_libs(self):
        """Importa osmnx y networkx."""
        try:
            import osmnx as ox
            import networkx as nx
            self._ox = ox
            self._nx = nx
        except ImportError:
            logger.warning("osmnx/networkx no disponibles — GeoEngine desactivado")

    def _cache_path(self, city: str) -> str:
        """Ruta del archivo cache para una ciudad."""
        slug = city.lower().replace(" ", "_")
        return os.path.join(CACHE_DIR, f"{slug}_drive.graphml")

    def load_city(self, city: str) -> bool:
        """Carga el grafo OSM de una ciudad (desde cache o descargando)."""
        if city in self._graphs:
            self._active_city = city
            return True

        if self._ox is None:
            return False

        config = CITY_CONFIGS.get(city)
        if not config:
            logger.warning(f"Ciudad '{city}' no configurada en CITY_CONFIGS")
            return False

        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_file = self._cache_path(city)

        # Intentar cargar desde cache
        if os.path.exists(cache_file):
            try:
                g = self._ox.load_graphml(cache_file)
                self._graphs[city] = g
                self._graphs_undirected[city] = g.to_undirected()
                self._active_city = city
                self.available = True
                logger.info(
                    f"GeoEngine loaded {city} (cache): "
                    f"{g.number_of_nodes()} nodos, "
                    f"{g.number_of_edges()} aristas"
                )
                return True
            except Exception as e:
                logger.warning(f"Error leyendo cache graphml de {city}: {e}")

        # Descargar el grafo desde OSM
        try:
            center = config["center"]
            dist = config["dist_m"]
            logger.info(
                f"Descargando grafo OSM de {city} "
                f"(radio {dist}m)... puede tardar 30-60s"
            )
            g = self._ox.graph_from_point(
                center, dist=dist,
                network_type="drive", simplify=True,
            )
            self._ox.save_graphml(g, cache_file)
            self._graphs[city] = g
            self._graphs_undirected[city] = g.to_undirected()
            self._active_city = city
            self.available = True
            logger.info(
                f"GeoEngine loaded {city} (descargado): "
                f"{g.number_of_nodes()} nodos, "
                f"{g.number_of_edges()} aristas"
            )
            return True
        except Exception as e:
            logger.error(f"No se pudo descargar grafo OSM de {city}: {e}")
            logger.warning(f"GeoEngine NO disponible para {city}")
            return False

    def _get_graphs(self, city: str | None):
        """Obtiene el par (dirigido, no-dirigido) para la ciudad solicitada."""
        city = city or self._active_city
        if city not in self._graphs:
            self.load_city(city)
        g = self._graphs.get(city)
        gu = self._graphs_undirected.get(city)
        return g, gu, city

    def shortest_route(self, origin: tuple, destination: tuple, city: str | None = None) -> list[tuple]:
        """
        Calcula la ruta mas corta entre dos coordenadas (lat, lon).
        Retorna lista de (lat, lon) representando la ruta por calles reales.
        Primero intenta grafo dirigido, si falla usa no-dirigido (ignora sentidos).
        Retorna lista vacia si no se puede calcular.
        """
        g, gu, city = self._get_graphs(city)
        if g is None:
            return []

        try:
            orig_node = self._ox.nearest_nodes(g, X=origin[1], Y=origin[0])
            dest_node = self._ox.nearest_nodes(g, X=destination[1], Y=destination[0])

            try:
                route_nodes = self._nx.shortest_path(
                    g, orig_node, dest_node, weight="length"
                )
            except self._nx.NetworkXNoPath:
                logger.debug("Sin ruta dirigida, usando grafo no-dirigido")
                route_nodes = self._nx.shortest_path(
                    gu, orig_node, dest_node, weight="length"
                )

            coords = []
            for node in route_nodes:
                data = g.nodes[node]
                coords.append((data["y"], data["x"]))

            return coords

        except Exception as e:
            logger.error(f"Error calculando ruta en {city}: {e}")
            return []

    def _ensure_travel_times(self, city: str | None = None):
        """Anade speed_kph y travel_time a las aristas si no existen."""
        city = city or self._active_city
        if city in self._travel_times:
            return

        g = self._graphs.get(city)
        gu = self._graphs_undirected.get(city)
        if g is None:
            return

        try:
            self._ox.add_edge_speeds(g)
            self._ox.add_edge_travel_times(g)
            if gu is not None:
                try:
                    self._ox.add_edge_speeds(gu)
                    self._ox.add_edge_travel_times(gu)
                except Exception:
                    for _, _, data in gu.edges(data=True):
                        length = data.get("length", 100)
                        data["travel_time"] = length / 11.1
            self._travel_times.add(city)
            logger.info(f"Travel times anadidos al grafo de {city}")
        except Exception as e:
            logger.warning(f"osmnx add_edge_speeds fallo para {city}: {e} — usando fallback 40km/h")
            for _, _, data in g.edges(data=True):
                length = data.get("length", 100)
                data["travel_time"] = length / 11.1
            if gu is not None:
                for _, _, data in gu.edges(data=True):
                    length = data.get("length", 100)
                    data["travel_time"] = length / 11.1
            self._travel_times.add(city)

    def fastest_route(
        self, origin: tuple, destination: tuple, traffic_zones: list[dict],
        city: str | None = None,
    ) -> list[tuple]:
        """
        Calcula la ruta mas rapida evitando zonas congestionadas.
        traffic_zones: lista de dicts con lat, lon, radius, congestion_factor.
        Retorna lista de (lat, lon). Lista vacia si falla.
        """
        g, gu, city = self._get_graphs(city)
        if g is None:
            return []

        try:
            self._ensure_travel_times(city)

            orig_node = self._ox.nearest_nodes(g, X=origin[1], Y=origin[0])
            dest_node = self._ox.nearest_nodes(g, X=destination[1], Y=destination[0])

            # Pre-computar congestion por nodo
            node_congestion = {}
            for node, ndata in g.nodes(data=True):
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

            # traffic_time = travel_time * congestion en cada arista
            for u, v, data in g.edges(data=True):
                base = data.get("travel_time", data.get("length", 100) / 11.1)
                cong = max(
                    node_congestion.get(u, 1.0),
                    node_congestion.get(v, 1.0),
                )
                data["traffic_time"] = base * cong

            try:
                route_nodes = self._nx.shortest_path(
                    g, orig_node, dest_node, weight="traffic_time"
                )
            except self._nx.NetworkXNoPath:
                logger.debug("Sin ruta dirigida (traffic), usando no-dirigido")
                for u, v, data in gu.edges(data=True):
                    base = data.get("travel_time", data.get("length", 100) / 11.1)
                    cong = max(
                        node_congestion.get(u, 1.0),
                        node_congestion.get(v, 1.0),
                    )
                    data["traffic_time"] = base * cong
                route_nodes = self._nx.shortest_path(
                    gu, orig_node, dest_node,
                    weight="traffic_time",
                )

            coords = []
            for node in route_nodes:
                data = g.nodes[node]
                coords.append((data["y"], data["x"]))

            return coords

        except Exception as e:
            logger.error(f"Error calculando ruta rapida en {city}: {e}")
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
