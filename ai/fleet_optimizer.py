"""
Optimizacion de Flota — Asigna vehiculos a emergencias minimizando tiempo.

Usa scipy.optimize.linear_sum_assignment (algoritmo hungaro) para encontrar
la asignacion optima vehiculo-emergencia.
"""

import math

try:
    from scipy.optimize import linear_sum_assignment
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# ── Constantes ───────────────────────────────────────────────────────────

AVG_SPEED_KMH = 50  # velocidad media de emergencia en ciudad
EARTH_RADIUS_KM = 6371.0

# Flota simulada por defecto
DEFAULT_FLEET = [
    {"id": "BOM-001", "type": "bomba_urbana", "lat": 39.4699, "lon": -0.3763, "available": True},
    {"id": "BOM-002", "type": "bomba_urbana", "lat": 39.4850, "lon": -0.3600, "available": True},
    {"id": "BOM-003", "type": "autoescalera", "lat": 39.4550, "lon": -0.3900, "available": True},
    {"id": "AMB-001", "type": "ambulancia", "lat": 39.4700, "lon": -0.3500, "available": True},
    {"id": "POL-001", "type": "policia", "lat": 39.4780, "lon": -0.3810, "available": True},
]


# ── Distancia haversine ─────────────────────────────────────────────────

def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en km entre dos puntos (lat/lon en grados)."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _travel_time_min(dist_km: float) -> float:
    """Tiempo estimado de viaje en minutos."""
    return (dist_km / AVG_SPEED_KMH) * 60


# ── Asignacion greedy (fallback) ────────────────────────────────────────

def _greedy_assign(vehicles: list, emergencies: list) -> list:
    """Asignacion greedy: cada emergencia se asigna al vehiculo libre mas cercano."""
    assigned_vehicles = set()
    assignments = []

    for emg in emergencies:
        best_v = None
        best_dist = float("inf")
        for v in vehicles:
            if v["id"] in assigned_vehicles or not v.get("available", True):
                continue
            d = _haversine(v["lat"], v["lon"], emg["lat"], emg["lon"])
            if d < best_dist:
                best_dist = d
                best_v = v

        if best_v:
            assigned_vehicles.add(best_v["id"])
            assignments.append({
                "vehicle_id": best_v["id"],
                "vehicle_type": best_v["type"],
                "emergency_id": emg.get("id", "E-?"),
                "distance_km": round(best_dist, 2),
                "eta_min": round(_travel_time_min(best_dist), 1),
            })

    return assignments


# ── API publica ──────────────────────────────────────────────────────────

def optimize(vehicles: list = None, emergencies: list = None) -> dict:
    """Asigna vehiculos a emergencias minimizando tiempo total de respuesta.

    Args:
        vehicles: Lista de dicts con id, type, lat, lon, available.
                  Si None, usa DEFAULT_FLEET.
        emergencies: Lista de dicts con id, lat, lon, priority.
                     Si None, genera ejemplo.

    Returns:
        dict con assignments, total_distance_km, avg_eta_min, method.
    """
    if vehicles is None:
        vehicles = DEFAULT_FLEET

    if emergencies is None:
        emergencies = [
            {"id": "E-001", "lat": 39.4737, "lon": -0.3755, "priority": "alta", "type": "incendio_vivienda"},
            {"id": "E-002", "lat": 39.4610, "lon": -0.3700, "priority": "media", "type": "accidente_trafico"},
        ]

    available = [v for v in vehicles if v.get("available", True)]

    if not available or not emergencies:
        return {
            "assignments": [],
            "total_distance_km": 0,
            "avg_eta_min": 0,
            "method": "none",
            "message": "Sin vehiculos disponibles o sin emergencias",
        }

    n_v = len(available)
    n_e = len(emergencies)

    if HAS_SCIPY and n_v >= 1 and n_e >= 1:
        # Construir matriz de costes (distancias)
        size = max(n_v, n_e)
        cost_matrix = []
        for i in range(size):
            row = []
            for j in range(size):
                if i < n_v and j < n_e:
                    d = _haversine(available[i]["lat"], available[i]["lon"],
                                   emergencies[j]["lat"], emergencies[j]["lon"])
                    row.append(d)
                else:
                    row.append(1e6)  # penalizacion para asignaciones ficticias
            cost_matrix.append(row)

        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        assignments = []
        total_dist = 0
        for r, c in zip(row_ind, col_ind):
            if r < n_v and c < n_e and cost_matrix[r][c] < 1e5:
                dist = cost_matrix[r][c]
                total_dist += dist
                assignments.append({
                    "vehicle_id": available[r]["id"],
                    "vehicle_type": available[r]["type"],
                    "emergency_id": emergencies[c].get("id", f"E-{c}"),
                    "emergency_type": emergencies[c].get("type", "desconocido"),
                    "distance_km": round(dist, 2),
                    "eta_min": round(_travel_time_min(dist), 1),
                    "priority": emergencies[c].get("priority", "media"),
                })

        assignments.sort(key=lambda x: x["eta_min"])
        method = "hungarian"
    else:
        assignments = _greedy_assign(available, emergencies)
        total_dist = sum(a["distance_km"] for a in assignments)
        method = "greedy_fallback"

    avg_eta = sum(a["eta_min"] for a in assignments) / len(assignments) if assignments else 0

    return {
        "assignments": assignments,
        "total_distance_km": round(total_dist, 2),
        "avg_eta_min": round(avg_eta, 1),
        "total_assignments": len(assignments),
        "vehicles_available": n_v,
        "emergencies_pending": n_e,
        "method": method,
    }


def coverage_score(vehicles: list = None, risk_zones: list = None) -> dict:
    """Calcula score de cobertura de la flota sobre zonas de riesgo.

    Score 0-1 que indica que tan bien cubre la flota las zonas de riesgo.
    Una zona se considera cubierta si hay un vehiculo a menos de 3 km.

    Args:
        vehicles: Lista de dicts con lat, lon. Si None, usa DEFAULT_FLEET.
        risk_zones: Lista de dicts con lat, lon, risk. Si None, genera desde predictive_deployment.

    Returns:
        dict con score, covered_zones, total_zones, details.
    """
    if vehicles is None:
        vehicles = DEFAULT_FLEET

    if risk_zones is None:
        try:
            from ai.predictive_deployment import analyze
            analysis = analyze(14)
            risk_zones = analysis.get("risk_zones", [])
        except Exception:
            risk_zones = [
                {"lat": 39.4737, "lon": -0.3755, "risk": 0.8, "zone_name": "Ciutat Vella"},
                {"lat": 39.4650, "lon": -0.3720, "risk": 0.7, "zone_name": "Eixample"},
                {"lat": 39.4610, "lon": -0.3700, "risk": 0.65, "zone_name": "Ruzafa"},
            ]

    if not risk_zones:
        return {"score": 1.0, "covered_zones": 0, "total_zones": 0, "details": []}

    coverage_radius_km = 3.0
    details = []
    covered = 0

    for zone in risk_zones:
        min_dist = float("inf")
        nearest_vehicle = None
        for v in vehicles:
            d = _haversine(v["lat"], v["lon"], zone["lat"], zone["lon"])
            if d < min_dist:
                min_dist = d
                nearest_vehicle = v.get("id", "?")

        is_covered = min_dist <= coverage_radius_km
        if is_covered:
            covered += 1

        details.append({
            "zone_name": zone.get("zone_name", "?"),
            "risk": zone.get("risk", 0),
            "nearest_vehicle": nearest_vehicle,
            "distance_km": round(min_dist, 2),
            "covered": is_covered,
        })

    score = covered / len(risk_zones) if risk_zones else 0

    return {
        "score": round(score, 3),
        "covered_zones": covered,
        "total_zones": len(risk_zones),
        "coverage_radius_km": coverage_radius_km,
        "details": details,
    }
