# Implementación: Simulación sobre Mapa Real con Tráfico

## Objetivo

Integrar cartografía real, tráfico en tiempo real y cálculo de rutas/ETA en el gemelo digital del camión de bomberos, permitiendo simulaciones geográficamente precisas.

---

## Arquitectura Propuesta

```
┌──────────────────────────────────────────────────────────┐
│                   CAPA DE DATOS GEOGRÁFICOS              │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │OpenStreetMap│  │ API Tráfico  │  │ Datos locales  │  │
│  │  (osmnx)   │  │ (Google/HERE)│  │ (hidrantes,    │  │
│  │            │  │              │  │  estaciones)   │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘  │
│         └────────────────┼──────────────────┘            │
│                          ▼                               │
│              ┌───────────────────────┐                   │
│              │   GeoEngine           │                   │
│              │   - Grafo de calles   │                   │
│              │   - Pesos de tráfico  │                   │
│              │   - Cálculo de rutas  │                   │
│              └───────────┬───────────┘                   │
└──────────────────────────┼───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│                   SIMULADOR DE MOVIMIENTO                │
│                                                          │
│  ┌─────────────────┐  ┌──────────────────────────────┐   │
│  │ RouteSimulator  │  │ TrafficAwareNavigator        │   │
│  │ - Posición GPS  │  │ - Recalculo dinámico de ruta │   │
│  │ - Velocidad     │  │ - ETA con congestión         │   │
│  │ - Heading       │  │ - Desvíos por bloqueos       │   │
│  └────────┬────────┘  └──────────────┬───────────────┘   │
│           └──────────────────────────┘                   │
│                          │                               │
│                          ▼                               │
│              ┌───────────────────────┐                   │
│              │ Publicación MQTT      │                   │
│              │ bomberos/telemetria/  │                   │
│              │   gps, eta, ruta      │                   │
│              └───────────────────────┘                   │
└──────────────────────────────────────────────────────────┘
```

---

## Componentes

### 1. GeoEngine — Motor Geográfico

Responsable de construir y mantener el grafo de calles navegable.

```python
import osmnx as ox
import networkx as nx

class GeoEngine:
    def __init__(self, city: str = "Valencia, Spain", radius_km: float = 15):
        self.graph = ox.graph_from_place(city, network_type="drive")
        self.graph = ox.speed.add_edge_speeds(self.graph)
        self.graph = ox.speed.add_edge_travel_times(self.graph)

    def shortest_route(self, origin: tuple, destination: tuple) -> dict:
        """Calcula ruta más corta por tiempo de viaje."""
        orig_node = ox.nearest_nodes(self.graph, origin[1], origin[0])
        dest_node = ox.nearest_nodes(self.graph, destination[1], destination[0])
        route = nx.shortest_path(self.graph, orig_node, dest_node, weight="travel_time")
        return {
            "nodes": route,
            "coords": [(self.graph.nodes[n]["y"], self.graph.nodes[n]["x"]) for n in route],
            "total_time_s": nx.shortest_path_length(self.graph, orig_node, dest_node, weight="travel_time"),
            "total_distance_m": nx.shortest_path_length(self.graph, orig_node, dest_node, weight="length")
        }

    def update_edge_weights(self, traffic_data: dict):
        """Actualiza pesos de aristas con datos de tráfico real."""
        for edge, congestion_factor in traffic_data.items():
            if edge in self.graph.edges:
                base_time = self.graph.edges[edge].get("travel_time", 0)
                self.graph.edges[edge]["travel_time"] = base_time * congestion_factor
```

### 2. TrafficProvider — Proveedor de Tráfico

Abstracción para obtener datos de tráfico de múltiples fuentes.

```python
from abc import ABC, abstractmethod

class TrafficProvider(ABC):
    @abstractmethod
    def get_travel_time(self, origin: tuple, destination: tuple) -> dict:
        pass

    @abstractmethod
    def get_congestion(self, bbox: tuple) -> dict:
        pass


class GoogleTrafficProvider(TrafficProvider):
    """Tráfico real via Google Routes API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://routes.googleapis.com"

    def get_travel_time(self, origin: tuple, destination: tuple) -> dict:
        # POST /directions/v2:computeRoutes
        # Header: X-Goog-FieldMask: routes.duration,routes.distanceMeters,routes.polyline
        # Devuelve duración con tráfico real incluido
        ...
        return {
            "duration_s": 482,
            "duration_in_traffic_s": 637,
            "distance_m": 5200,
            "congestion_ratio": 1.32,  # 32% más lento que sin tráfico
            "polyline": "encoded_polyline..."
        }

    def get_congestion(self, bbox: tuple) -> dict:
        # Consulta nivel de congestión por zona
        ...


class OpenRouteProvider(TrafficProvider):
    """Alternativa gratuita con OpenRouteService."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openrouteservice.org"

    def get_travel_time(self, origin: tuple, destination: tuple) -> dict:
        # GET /v2/directions/driving-car
        # Gratuito, sin tráfico real pero con estimaciones de velocidad por tipo de vía
        ...


class SimulatedTrafficProvider(TrafficProvider):
    """Tráfico simulado para desarrollo y POC (sin coste)."""

    def __init__(self, congestion_model: str = "time_based"):
        self.congestion_model = congestion_model

    def get_congestion_factor(self, hour: int) -> float:
        """Modelo simple: hora punta = más congestión."""
        peak_hours = {7: 1.6, 8: 1.8, 9: 1.5, 13: 1.3, 14: 1.4, 17: 1.5, 18: 1.8, 19: 1.6}
        return peak_hours.get(hour, 1.0)
```

### 3. RouteSimulator — Simulador de Movimiento

Mueve el vehículo por la ruta calculada tick a tick.

```python
import time
from dataclasses import dataclass

@dataclass
class VehiclePosition:
    latitude: float
    longitude: float
    speed_kmh: float
    heading: float
    route_progress: float       # 0.0 - 1.0
    eta_seconds: float
    distance_remaining_m: float

class RouteSimulator:
    def __init__(self, geo_engine: GeoEngine, tick_interval_s: float = 1.0):
        self.geo = geo_engine
        self.tick_interval = tick_interval_s
        self.current_route = None
        self.current_index = 0
        self.emergency_speed_factor = 1.4  # Bomberos circulan ~40% más rápido con sirenas

    def start_mission(self, origin: tuple, destination: tuple, emergency: bool = True):
        """Inicia una nueva misión con ruta calculada."""
        self.current_route = self.geo.shortest_route(origin, destination)
        self.current_index = 0
        if emergency:
            self.current_route["total_time_s"] /= self.emergency_speed_factor
        return self.current_route

    def tick(self) -> VehiclePosition:
        """Avanza un tick en la simulación. Retorna posición actualizada."""
        coords = self.current_route["coords"]
        if self.current_index >= len(coords) - 1:
            return self._arrived_position()

        current = coords[self.current_index]
        next_point = coords[self.current_index + 1]

        # Calcular heading entre dos puntos
        heading = self._calculate_heading(current, next_point)

        # Calcular velocidad basada en tipo de vía + tráfico
        speed = self._calculate_speed()

        self.current_index += 1
        progress = self.current_index / (len(coords) - 1)

        return VehiclePosition(
            latitude=next_point[0],
            longitude=next_point[1],
            speed_kmh=speed,
            heading=heading,
            route_progress=progress,
            eta_seconds=self.current_route["total_time_s"] * (1 - progress),
            distance_remaining_m=self.current_route["total_distance_m"] * (1 - progress)
        )

    def recalculate_route(self, current_pos: tuple, destination: tuple):
        """Recalcula ruta desde posición actual (desvío, bloqueo, etc)."""
        self.current_route = self.geo.shortest_route(current_pos, destination)
        self.current_index = 0
```

### 4. Integración con el Gemelo Digital

```python
class FireTruckTwin:
    def __init__(self, vehicle_id: str, geo_engine: GeoEngine, traffic: TrafficProvider):
        self.vehicle_id = vehicle_id
        self.route_sim = RouteSimulator(geo_engine)
        self.traffic = traffic
        self.mqtt_client = mqtt.Client()

    async def dispatch_to_fire(self, fire_location: tuple):
        """Despachar camión a un incendio."""
        current_pos = (self.state.latitude, self.state.longitude)

        # Calcular ruta óptima
        route = self.route_sim.start_mission(current_pos, fire_location, emergency=True)

        # Publicar ruta y ETA inicial
        self.mqtt_client.publish(f"bomberos/telemetria/{self.vehicle_id}/route", json.dumps({
            "destination": fire_location,
            "eta_seconds": route["total_time_s"],
            "distance_m": route["total_distance_m"],
            "polyline": route["coords"]
        }))

        # Simular movimiento tick a tick
        while True:
            position = self.route_sim.tick()
            self.state.latitude = position.latitude
            self.state.longitude = position.longitude
            self.state.speed_kmh = position.speed_kmh

            # Publicar posición
            self.mqtt_client.publish(
                f"bomberos/telemetria/{self.vehicle_id}/gps",
                json.dumps(asdict(position))
            )

            if position.route_progress >= 1.0:
                self.state.mission_status = "en_escena"
                break

            await asyncio.sleep(self.route_sim.tick_interval)
```

---

## Visualización en Dashboard

### Opción A: Streamlit + Folium (simple, para POC)

```python
import streamlit as st
import folium
from streamlit_folium import st_folium

def render_map(vehicle_state, route_coords, fire_location):
    m = folium.Map(location=[vehicle_state.latitude, vehicle_state.longitude], zoom_start=14)

    # Ruta del camión
    folium.PolyLine(route_coords, color="blue", weight=4, opacity=0.7).add_to(m)

    # Posición actual del camión
    folium.Marker(
        [vehicle_state.latitude, vehicle_state.longitude],
        icon=folium.Icon(color="red", icon="fire", prefix="fa"),
        popup=f"BOM-001 | {vehicle_state.speed_kmh:.0f} km/h"
    ).add_to(m)

    # Ubicación del incendio
    folium.Marker(
        fire_location,
        icon=folium.Icon(color="orange", icon="fire-extinguisher", prefix="fa"),
        popup="Incendio activo"
    ).add_to(m)

    # ETA
    folium.Marker(
        [vehicle_state.latitude, vehicle_state.longitude],
        icon=folium.DivIcon(html=f'<div style="font-weight:bold;color:red">ETA: {vehicle_state.eta}s</div>')
    ).add_to(m)

    st_folium(m, width=800, height=500)
```

### Opción B: Deck.gl / Mapbox GL (avanzado, tiempo real)

Para streaming fluido con WebSocket, usar `pydeck` o frontend con Mapbox GL JS que consuma el WebSocket del gemelo directamente.

---

## APIs de Tráfico — Comparativa

| Proveedor | Tráfico Real | Coste | Límite Gratuito | Latencia |
|-----------|:------------:|-------|-----------------|----------|
| Google Routes API | Sí | ~$5/1000 req | $200 crédito/mes | ~100ms |
| HERE Routing | Sí | ~$4.5/1000 req | 250K req/mes | ~120ms |
| TomTom Routing | Sí | ~$4/1000 req | 2500 req/día | ~150ms |
| Mapbox Directions | Sí | ~$2/1000 req | 100K req/mes | ~100ms |
| OpenRouteService | No (estimado) | Gratis | 2000 req/día | ~200ms |
| OSMnx + NetworkX | No (simulado) | Gratis | Sin límite (local) | ~5ms |

### Estrategia recomendada para el POC

```
Fase 1 (POC):     OSMnx + SimulatedTrafficProvider     → Coste $0
Fase 2 (Demo):    OSMnx + OpenRouteService              → Coste $0
Fase 3 (Producción): OSMnx + Google/HERE API            → Coste variable
```

---

## Datos Complementarios para Realismo

### Hidrantes y puntos de agua

```python
import osmnx as ox

# Obtener hidrantes de OpenStreetMap
hydrants = ox.features_from_place("Valencia, Spain", tags={"emergency": "fire_hydrant"})
# Devuelve GeoDataFrame con ubicación de cada hidrante

# Integrar en decisiones
def nearest_hydrant(vehicle_pos: tuple, hydrants_gdf) -> dict:
    """Encuentra hidrante más cercano al camión."""
    from shapely.geometry import Point
    veh_point = Point(vehicle_pos[1], vehicle_pos[0])
    hydrants_gdf["distance"] = hydrants_gdf.geometry.distance(veh_point)
    nearest = hydrants_gdf.loc[hydrants_gdf["distance"].idxmin()]
    return {
        "location": (nearest.geometry.y, nearest.geometry.x),
        "distance_m": nearest["distance"] * 111320  # aprox grados a metros
    }
```

### Estaciones de bomberos

```python
# Obtener estaciones de bomberos de OSM
stations = ox.features_from_place("Valencia, Spain", tags={"amenity": "fire_station"})
```

### Edificios (para simulación de incendios)

```python
# Obtener edificios con altura (para simular rescates en altura)
buildings = ox.features_from_place("Valencia, Spain", tags={"building": True})
# Filtrar edificios altos que requieran escalera
tall_buildings = buildings[buildings["building:levels"].astype(float) > 5]
```

---

## Escenarios What-If con Mapa Real

### Ejemplo: Despacho óptimo ante incendio

```python
async def simulate_optimal_dispatch(fire_location, available_units, geo_engine, traffic):
    """¿Qué unidad llega primero considerando tráfico real?"""
    results = []

    for unit in available_units:
        unit_pos = (unit.latitude, unit.longitude)
        travel = traffic.get_travel_time(unit_pos, fire_location)
        route = geo_engine.shortest_route(unit_pos, fire_location)

        results.append({
            "unit_id": unit.vehicle_id,
            "eta_seconds": travel["duration_in_traffic_s"],
            "distance_m": travel["distance_m"],
            "congestion_ratio": travel["congestion_ratio"],
            "route": route["coords"],
            "water_tank": unit.water_tank_level,
            "crew": unit.crew_count
        })

    # Ordenar por ETA
    results.sort(key=lambda x: x["eta_seconds"])

    # La unidad más cercana no siempre es la mejor
    # Considerar también nivel de agua y tripulación
    return rank_by_composite_score(results)
```

### Ejemplo: Cobertura de zona con N unidades

```python
def analyze_coverage(stations, geo_engine, max_response_time_s=300):
    """¿Qué porcentaje de la ciudad está cubierta en < 5 minutos?"""
    from shapely.geometry import MultiPoint
    import geopandas as gpd

    isochrones = []
    for station in stations:
        # Generar isócrona: todas las calles alcanzables en max_response_time_s
        reachable = nx.ego_graph(
            geo_engine.graph, station.node_id,
            radius=max_response_time_s, distance="travel_time"
        )
        points = [(geo_engine.graph.nodes[n]["x"], geo_engine.graph.nodes[n]["y"])
                   for n in reachable.nodes]
        isochrones.append(MultiPoint(points).convex_hull)

    # Calcular cobertura total vs área de la ciudad
    total_coverage = gpd.GeoSeries(isochrones).unary_union
    return total_coverage
```

---

## Dependencias Adicionales

```
# Geoespacial
osmnx==1.9.1
networkx==3.2.1
geopandas==0.14.3
shapely==2.0.2
folium==0.15.1
streamlit-folium==0.18.0

# APIs de tráfico (elegir una)
googlemaps==4.10.0          # Google
# here-routing==1.0.0       # HERE
# openrouteservice==2.3.3   # ORS (gratuito)
```

---

## Resumen

| Aspecto | Solución |
|---------|----------|
| Mapa real | OpenStreetMap via `osmnx` |
| Grafo navegable | `networkx` sobre grafo OSM |
| Tráfico real | Google Routes API / HERE / Mapbox |
| Tráfico simulado (POC) | Modelo hora-punta propio |
| Cálculo de rutas | Dijkstra/A* sobre grafo con pesos de tráfico |
| ETA dinámico | Recálculo cada N segundos con tráfico actualizado |
| Visualización | Folium (POC) → Mapbox GL JS (producción) |
| Datos extra | Hidrantes, estaciones, edificios desde OSM |
| Coste POC | $0 (todo local/gratuito) |
