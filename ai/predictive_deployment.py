"""
Despliegue Predictivo — Identifica zonas de alto riesgo segun hora del dia.

Usa KMeans (scikit-learn) sobre datos sinteticos de incidentes historicos
en Valencia para crear clusters de riesgo y recomendar posiciones de vehiculos.
"""

import math
import random

import numpy as np

try:
    from sklearn.cluster import KMeans
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


# ── Zonas reales de Valencia con patrones temporales ─────────────────────

ZONES = [
    # Residencial — cocina 12-14h y 20-22h
    {"name": "Ciutat Vella", "lat": 39.4737, "lon": -0.3755, "hours": [12, 13, 20, 21], "weight": 3},
    {"name": "Eixample", "lat": 39.4650, "lon": -0.3720, "hours": [12, 13, 14, 20, 21, 22], "weight": 4},
    {"name": "Ruzafa", "lat": 39.4610, "lon": -0.3700, "hours": [13, 14, 20, 21], "weight": 3},
    {"name": "Benimaclet", "lat": 39.4880, "lon": -0.3580, "hours": [12, 13, 21, 22], "weight": 2},
    {"name": "Patraix", "lat": 39.4590, "lon": -0.3890, "hours": [13, 14, 20, 21], "weight": 2},
    # Industrial — horario laboral 9-17h
    {"name": "Poligono Vara de Quart", "lat": 39.4620, "lon": -0.4100, "hours": [9, 10, 11, 14, 15, 16], "weight": 3},
    {"name": "Zona Portuaria", "lat": 39.4450, "lon": -0.3300, "hours": [8, 9, 10, 11, 15, 16, 17], "weight": 3},
    {"name": "Poligono Fuente del Jarro", "lat": 39.5100, "lon": -0.4600, "hours": [9, 10, 11, 14, 15], "weight": 2},
    # Nocturno — ocio 0-4h
    {"name": "Zona Marina Real", "lat": 39.4630, "lon": -0.3280, "hours": [0, 1, 2, 3], "weight": 2},
    {"name": "Barrio del Carmen", "lat": 39.4780, "lon": -0.3810, "hours": [0, 1, 2, 3, 4], "weight": 3},
    # Forestal — tarde calurosa 14-18h
    {"name": "Parque Natural Albufera", "lat": 39.3500, "lon": -0.3500, "hours": [14, 15, 16, 17, 18], "weight": 2},
    {"name": "Sierra Calderona", "lat": 39.6700, "lon": -0.4200, "hours": [13, 14, 15, 16, 17], "weight": 2},
]


def _generate_synthetic_incidents(n=200, seed=42):
    """Genera dataset sintetico de incidentes historicos."""
    rng = random.Random(seed)
    incidents = []
    for _ in range(n):
        zone = rng.choices(ZONES, weights=[z["weight"] for z in ZONES], k=1)[0]
        hour = rng.choice(zone["hours"])
        lat = zone["lat"] + rng.gauss(0, 0.005)
        lon = zone["lon"] + rng.gauss(0, 0.005)
        incidents.append({"lat": lat, "lon": lon, "hour": hour, "zone": zone["name"]})
    return incidents


# ── Modelo KMeans ────────────────────────────────────────────────────────

_incidents = _generate_synthetic_incidents()
_model = None
_cluster_centers = None
_cluster_labels = None


def _train_model(n_clusters=6):
    global _model, _cluster_centers, _cluster_labels
    if not HAS_SKLEARN:
        return

    X = np.array([[inc["lat"], inc["lon"], inc["hour"] / 24.0] for inc in _incidents])
    _model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    _cluster_labels = _model.fit_predict(X)
    _cluster_centers = _model.cluster_centers_


_train_model()


# ── Tabla estatica (fallback) ────────────────────────────────────────────

_STATIC_RISK = {
    "manana": [
        {"zone_name": "Poligono Vara de Quart", "lat": 39.4620, "lon": -0.4100, "risk": 0.7},
        {"zone_name": "Zona Portuaria", "lat": 39.4450, "lon": -0.3300, "risk": 0.65},
    ],
    "mediodia": [
        {"zone_name": "Eixample", "lat": 39.4650, "lon": -0.3720, "risk": 0.8},
        {"zone_name": "Ciutat Vella", "lat": 39.4737, "lon": -0.3755, "risk": 0.7},
        {"zone_name": "Ruzafa", "lat": 39.4610, "lon": -0.3700, "risk": 0.65},
    ],
    "tarde": [
        {"zone_name": "Parque Natural Albufera", "lat": 39.3500, "lon": -0.3500, "risk": 0.75},
        {"zone_name": "Sierra Calderona", "lat": 39.6700, "lon": -0.4200, "risk": 0.6},
    ],
    "noche": [
        {"zone_name": "Eixample", "lat": 39.4650, "lon": -0.3720, "risk": 0.8},
        {"zone_name": "Ruzafa", "lat": 39.4610, "lon": -0.3700, "risk": 0.7},
    ],
    "madrugada": [
        {"zone_name": "Barrio del Carmen", "lat": 39.4780, "lon": -0.3810, "risk": 0.75},
        {"zone_name": "Zona Marina Real", "lat": 39.4630, "lon": -0.3280, "risk": 0.6},
    ],
}


def _hour_to_period(hour: int) -> str:
    if 6 <= hour < 12:
        return "manana"
    elif 12 <= hour < 15:
        return "mediodia"
    elif 15 <= hour < 20:
        return "tarde"
    elif 20 <= hour < 24:
        return "noche"
    else:
        return "madrugada"


# ── API publica ──────────────────────────────────────────────────────────

def analyze(hour: int = 14) -> dict:
    """Analiza zonas de riesgo para una hora del dia.

    Returns dict con risk_zones (lista de zonas con lat, lon, risk, zone_name).
    """
    hour = max(0, min(23, hour))

    if HAS_SKLEARN and _model is not None:
        # Filtrar incidentes cercanos a la hora
        relevant = [inc for inc in _incidents if abs(inc["hour"] - hour) <= 2
                     or abs(inc["hour"] - hour) >= 22]  # wrap around midnight

        if not relevant:
            relevant = _incidents

        X = np.array([[inc["lat"], inc["lon"], inc["hour"] / 24.0] for inc in relevant])
        labels = _model.predict(X)

        # Agrupar por cluster y calcular riesgo
        clusters = {}
        for i, label in enumerate(labels):
            label = int(label)
            if label not in clusters:
                clusters[label] = {"lats": [], "lons": [], "count": 0}
            clusters[label]["lats"].append(relevant[i]["lat"])
            clusters[label]["lons"].append(relevant[i]["lon"])
            clusters[label]["count"] += 1

        total = len(relevant)
        risk_zones = []
        for cluster_id, data in clusters.items():
            risk = min(data["count"] / total * 3, 1.0)  # normalizar
            center_lat = sum(data["lats"]) / len(data["lats"])
            center_lon = sum(data["lons"]) / len(data["lons"])

            # Buscar nombre de zona mas cercana
            min_dist = float("inf")
            zone_name = "Zona desconocida"
            for z in ZONES:
                d = math.sqrt((z["lat"] - center_lat) ** 2 + (z["lon"] - center_lon) ** 2)
                if d < min_dist:
                    min_dist = d
                    zone_name = z["name"]

            risk_zones.append({
                "zone_name": zone_name,
                "lat": round(center_lat, 6),
                "lon": round(center_lon, 6),
                "risk": round(risk, 3),
                "incident_count": data["count"],
                "cluster_id": cluster_id,
            })

        risk_zones.sort(key=lambda x: x["risk"], reverse=True)
        method = "kmeans"
    else:
        period = _hour_to_period(hour)
        risk_zones = _STATIC_RISK.get(period, _STATIC_RISK["mediodia"])
        method = "static_fallback"

    return {
        "hour": hour,
        "method": method,
        "risk_zones": risk_zones,
        "total_zones": len(risk_zones),
    }


def recommend_positions(hour: int = 14, n_vehicles: int = 3) -> dict:
    """Recomienda posiciones optimas para N vehiculos segun riesgo.

    Distribuye vehiculos en las zonas de mayor riesgo ponderado.
    """
    analysis = analyze(hour)
    zones = analysis["risk_zones"]

    if not zones:
        return {"hour": hour, "positions": [], "method": analysis["method"]}

    # Asignar vehiculos a zonas de mayor riesgo
    positions = []
    for i in range(min(n_vehicles, len(zones))):
        zone = zones[i]
        positions.append({
            "vehicle_slot": i + 1,
            "lat": zone["lat"],
            "lon": zone["lon"],
            "zone_name": zone["zone_name"],
            "risk_level": zone["risk"],
            "priority": "alta" if zone["risk"] > 0.6 else "media" if zone["risk"] > 0.3 else "baja",
        })

    # Si hay mas vehiculos que zonas, repartir extras en zonas top
    if n_vehicles > len(zones):
        for i in range(len(zones), n_vehicles):
            zone = zones[i % len(zones)]
            offset_lat = random.gauss(0, 0.003)
            offset_lon = random.gauss(0, 0.003)
            positions.append({
                "vehicle_slot": i + 1,
                "lat": round(zone["lat"] + offset_lat, 6),
                "lon": round(zone["lon"] + offset_lon, 6),
                "zone_name": zone["zone_name"] + " (refuerzo)",
                "risk_level": zone["risk"],
                "priority": "refuerzo",
            })

    return {
        "hour": hour,
        "n_vehicles": n_vehicles,
        "positions": positions,
        "method": analysis["method"],
        "coverage_zones": len(zones),
    }
