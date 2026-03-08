"""
SimulatedTrafficProvider — modelo de congestion por hora punta.
Factor de congestion: 1.0 = fluido, hasta ~1.8 en hora punta.
Soporte multi-ciudad con zonas de trafico por ciudad.
"""

from datetime import datetime


# Franjas de hora punta y su factor extra de congestion
_PEAK_WINDOWS = [
    ((7, 0), (9, 0), 0.7),    # manana
    ((13, 0), (14, 30), 0.4),  # mediodia
    ((17, 0), (19, 30), 0.6),  # tarde
]

# Factor base (trafico nocturno / fuera de hora punta)
_BASE_FACTOR = 1.0


class SimulatedTrafficProvider:
    """Provee un factor de congestion simulado segun la hora del dia."""

    @staticmethod
    def congestion_factor(dt: datetime | None = None) -> float:
        """
        Retorna un factor de congestion entre 1.0 (fluido) y ~1.8 (muy congestionado).
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
                # Parabola invertida: maximo en el centro
                extra = max(extra, peak * (1 - dist ** 2))

        return round(_BASE_FACTOR + extra, 2)

    @staticmethod
    def describe(factor: float) -> str:
        """Descripcion textual del nivel de congestion."""
        if factor < 1.15:
            return "fluido"
        elif factor < 1.35:
            return "moderado"
        elif factor < 1.55:
            return "congestionado"
        else:
            return "muy congestionado"


# ── Zonas de trafico por ciudad ─────────────────────────────────────────────

TRAFFIC_ZONES_BY_CITY = {
    "Valencia": [
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
    ],
    "Madrid": [
        {"name": "Gran Via", "lat": 40.4200, "lon": -3.7105, "radius": 220},
        {"name": "Paseo de la Castellana Norte", "lat": 40.4510, "lon": -3.6920, "radius": 250},
        {"name": "Paseo de la Castellana Sur", "lat": 40.4280, "lon": -3.6930, "radius": 230},
        {"name": "Calle de Alcala", "lat": 40.4190, "lon": -3.7010, "radius": 200},
        {"name": "Puerta del Sol", "lat": 40.4168, "lon": -3.7038, "radius": 150},
        {"name": "Calle Serrano", "lat": 40.4290, "lon": -3.6860, "radius": 190},
        {"name": "Atocha", "lat": 40.4070, "lon": -3.6930, "radius": 210},
        {"name": "Plaza de Cibeles", "lat": 40.4195, "lon": -3.6930, "radius": 170},
        {"name": "Calle Princesa", "lat": 40.4300, "lon": -3.7180, "radius": 180},
        {"name": "M-30 Sur", "lat": 40.3900, "lon": -3.6900, "radius": 280},
        {"name": "Calle Bravo Murillo", "lat": 40.4470, "lon": -3.7040, "radius": 200},
        {"name": "Av. de America", "lat": 40.4380, "lon": -3.6700, "radius": 220},
    ],
    "Barcelona": [
        {"name": "Passeig de Gracia", "lat": 41.3920, "lon": 2.1650, "radius": 200},
        {"name": "La Rambla", "lat": 41.3809, "lon": 2.1740, "radius": 180},
        {"name": "Avinguda Diagonal Eix.", "lat": 41.3940, "lon": 2.1560, "radius": 240},
        {"name": "Avinguda Diagonal Glories", "lat": 41.4030, "lon": 2.1870, "radius": 230},
        {"name": "Gran Via de les Corts Catalanes", "lat": 41.3880, "lon": 2.1530, "radius": 220},
        {"name": "Avinguda Meridiana", "lat": 41.4120, "lon": 2.1850, "radius": 210},
        {"name": "Ronda de Dalt", "lat": 41.4250, "lon": 2.1600, "radius": 260},
        {"name": "Ronda Litoral", "lat": 41.3700, "lon": 2.1680, "radius": 240},
        {"name": "Via Laietana", "lat": 41.3850, "lon": 2.1770, "radius": 170},
        {"name": "Carrer d'Arago", "lat": 41.3900, "lon": 2.1650, "radius": 190},
        {"name": "Placa Catalunya", "lat": 41.3874, "lon": 2.1686, "radius": 140},
        {"name": "Av. Paral-lel", "lat": 41.3750, "lon": 2.1620, "radius": 180},
    ],
    "Sevilla": [
        {"name": "Av. de la Constitucion", "lat": 37.3860, "lon": -5.9930, "radius": 180},
        {"name": "Ronda del Tamarguillo", "lat": 37.3870, "lon": -5.9720, "radius": 220},
        {"name": "Av. Kansas City", "lat": 37.3790, "lon": -5.9680, "radius": 200},
        {"name": "Puente del Alamillo", "lat": 37.4000, "lon": -5.9980, "radius": 170},
        {"name": "Calle San Fernando", "lat": 37.3830, "lon": -5.9870, "radius": 160},
        {"name": "Av. de la Palmera", "lat": 37.3720, "lon": -5.9850, "radius": 190},
        {"name": "Ronda de Capuchinos", "lat": 37.4010, "lon": -5.9860, "radius": 180},
        {"name": "Puente de Triana", "lat": 37.3855, "lon": -5.9980, "radius": 150},
        {"name": "Av. de Eduardo Dato", "lat": 37.3880, "lon": -5.9650, "radius": 200},
        {"name": "SE-30 Oeste", "lat": 37.3950, "lon": -6.0100, "radius": 250},
    ],
    "Bilbao": [
        {"name": "Gran Via Don Diego Lopez de Haro", "lat": 43.2640, "lon": -2.9350, "radius": 190},
        {"name": "Alameda de Mazarredo", "lat": 43.2660, "lon": -2.9370, "radius": 170},
        {"name": "Av. Sabino Arana", "lat": 43.2700, "lon": -2.9500, "radius": 180},
        {"name": "Puente de La Salve", "lat": 43.2685, "lon": -2.9340, "radius": 150},
        {"name": "Calle Autonomia", "lat": 43.2620, "lon": -2.9420, "radius": 170},
        {"name": "Av. Lehendakari Aguirre", "lat": 43.2740, "lon": -2.9460, "radius": 200},
        {"name": "Calle Hurtado de Amezaga", "lat": 43.2610, "lon": -2.9300, "radius": 160},
        {"name": "Calle Ercilla", "lat": 43.2630, "lon": -2.9400, "radius": 155},
        {"name": "Puente del Arenal", "lat": 43.2590, "lon": -2.9280, "radius": 140},
        {"name": "Campo Volantin", "lat": 43.2670, "lon": -2.9420, "radius": 165},
    ],
}

# Offset fijo por zona: calles centricas siempre mas congestionadas
# Valores altos fuerzan al router a buscar rutas alternativas
_ZONE_WEIGHTS_BY_CITY = {
    "Valencia": [0.1, -0.05, 0.8, 0.7, 0.05, 0.75, -0.05, 0.25, 0.6, 0.05, 0.8, 0.15],
    "Madrid": [0.7, 0.1, 0.15, 0.6, 0.8, 0.3, 0.2, 0.65, 0.4, 0.05, 0.15, 0.1],
    "Barcelona": [0.7, 0.6, 0.15, 0.1, 0.2, 0.1, 0.05, 0.05, 0.5, 0.25, 0.75, 0.3],
    "Sevilla": [0.6, 0.1, 0.05, 0.15, 0.5, 0.1, 0.2, 0.4, 0.1, 0.05],
    "Bilbao": [0.7, 0.4, 0.15, 0.3, 0.25, 0.1, 0.5, 0.2, 0.35, 0.15],
}

# Compat: mantener TRAFFIC_ZONES como alias de Valencia
TRAFFIC_ZONES = TRAFFIC_ZONES_BY_CITY["Valencia"]


def get_zones_with_congestion(dt=None, city="Valencia"):
    """Retorna zonas de trafico con factor de congestion actual por zona."""
    base = SimulatedTrafficProvider.congestion_factor(dt)
    zones = TRAFFIC_ZONES_BY_CITY.get(city, TRAFFIC_ZONES_BY_CITY["Valencia"])
    weights = _ZONE_WEIGHTS_BY_CITY.get(city, _ZONE_WEIGHTS_BY_CITY["Valencia"])
    result = []
    for i, z in enumerate(zones):
        extra = weights[i] if i < len(weights) else 0.0
        factor = round(base + extra, 2)
        factor = max(1.0, min(factor, 2.0))
        result.append({**z, "congestion_factor": factor})
    return result
