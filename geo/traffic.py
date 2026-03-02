"""
SimulatedTrafficProvider — modelo de congestión por hora punta en Valencia.
Factor de congestión: 1.0 = fluido, hasta ~1.8 en hora punta.
"""

from datetime import datetime


# Franjas de hora punta y su factor extra de congestión
_PEAK_WINDOWS = [
    ((7, 0), (9, 0), 0.7),    # mañana
    ((13, 0), (14, 30), 0.4),  # mediodía
    ((17, 0), (19, 30), 0.6),  # tarde
]

# Factor base (tráfico nocturno / fuera de hora punta)
_BASE_FACTOR = 1.0


class SimulatedTrafficProvider:
    """Provee un factor de congestión simulado según la hora del día."""

    @staticmethod
    def congestion_factor(dt: datetime | None = None) -> float:
        """
        Retorna un factor de congestión entre 1.0 (fluido) y ~1.8 (muy congestionado).
        El factor multiplica el tiempo estimado de recorrido.
        """
        if dt is None:
            dt = datetime.now()

        minutes = dt.hour * 60 + dt.minute
        extra = 0.0

        for (sh, sm), (eh, em), peak in _PEAK_WINDOWS:
            start = sh * 60 + sm
            end = eh * 60 + em
            if start <= minutes <= end:
                # Forma de campana dentro de la franja
                mid = (start + end) / 2
                half = (end - start) / 2
                dist = abs(minutes - mid) / half  # 0..1
                # Parábola invertida: máximo en el centro
                extra = max(extra, peak * (1 - dist ** 2))

        return round(_BASE_FACTOR + extra, 2)

    @staticmethod
    def describe(factor: float) -> str:
        """Descripción textual del nivel de congestión."""
        if factor < 1.15:
            return "fluido"
        elif factor < 1.35:
            return "moderado"
        elif factor < 1.55:
            return "congestionado"
        else:
            return "muy congestionado"


# Zonas de tráfico simulado en calles principales de Valencia
TRAFFIC_ZONES = [
    {"name": "Gran Via Marques del Turia", "lat": 39.4665, "lon": -0.3700, "radius": 200},
    {"name": "Av. del Puerto", "lat": 39.4620, "lon": -0.3650, "radius": 180},
    {"name": "Calle Colon", "lat": 39.4700, "lon": -0.3730, "radius": 170},
    {"name": "Calle San Vicente", "lat": 39.4730, "lon": -0.3780, "radius": 160},
    {"name": "Av. del Cid", "lat": 39.4650, "lon": -0.3830, "radius": 190},
    {"name": "Calle Xativa", "lat": 39.4680, "lon": -0.3770, "radius": 150},
    {"name": "Av. Blasco Ibanez", "lat": 39.4800, "lon": -0.3650, "radius": 210},
    {"name": "Puente de Aragon", "lat": 39.4710, "lon": -0.3680, "radius": 140},
    {"name": "Gran Via Germanias", "lat": 39.4660, "lon": -0.3760, "radius": 170},
    {"name": "Av. Peris y Valero", "lat": 39.4600, "lon": -0.3730, "radius": 180},
    {"name": "Plaza del Ayuntamiento", "lat": 39.4699, "lon": -0.3763, "radius": 130},
    {"name": "Torres de Serranos", "lat": 39.4790, "lon": -0.3760, "radius": 120},
]

# Offset fijo por zona: calles céntricas siempre más congestionadas
# Valores altos fuerzan al router a buscar rutas alternativas
_ZONE_WEIGHTS = [0.1, -0.05, 0.8, 0.7, 0.05, 0.75, -0.05, 0.25, 0.6, 0.05, 0.8, 0.15]


def get_zones_with_congestion(dt=None):
    """Retorna zonas de tráfico con factor de congestión actual por zona."""
    base = SimulatedTrafficProvider.congestion_factor(dt)
    zones = []
    for i, z in enumerate(TRAFFIC_ZONES):
        extra = _ZONE_WEIGHTS[i] if i < len(_ZONE_WEIGHTS) else 0.0
        factor = round(base + extra, 2)
        factor = max(1.0, min(factor, 2.0))
        zones.append({**z, "congestion_factor": factor})
    return zones
