"""
Estimador de Recursos — Dado tipo de incidente y severidad, estima recursos.

Usa DecisionTreeRegressor (scikit-learn) entrenado con datos sinteticos
para predecir bomberos, agua, espuma, vehiculos y tiempo necesarios.
"""

import random

import numpy as np

try:
    from sklearn.tree import DecisionTreeRegressor
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


# ── Tipos de incidente ───────────────────────────────────────────────────

INCIDENT_TYPES = {
    "incendio_vivienda": {
        "description": "Incendio en edificio residencial o vivienda unifamiliar",
        "icon": "house-fire",
    },
    "incendio_industrial": {
        "description": "Incendio en nave industrial, almacen o fabrica",
        "icon": "industry",
    },
    "accidente_trafico": {
        "description": "Accidente de trafico con posible atrapamiento o derrame",
        "icon": "car-burst",
    },
    "rescate_altura": {
        "description": "Rescate en altura, derrumbe o personas atrapadas",
        "icon": "person-falling",
    },
    "incendio_forestal": {
        "description": "Incendio de vegetacion, monte o zona natural",
        "icon": "tree",
    },
    "fuga_quimica": {
        "description": "Fuga o derrame de sustancias quimicas o peligrosas",
        "icon": "biohazard",
    },
}

SEVERITIES = ["baja", "media", "alta"]

# ── Tabla de lookup (base + fallback) ────────────────────────────────────

_RESOURCE_TABLE = {
    ("incendio_vivienda", "baja"):  {"bomberos": 4,  "agua_litros": 2000,  "espuma_litros": 0,    "vehiculos": 1, "tiempo_min": 30},
    ("incendio_vivienda", "media"): {"bomberos": 8,  "agua_litros": 5000,  "espuma_litros": 200,  "vehiculos": 2, "tiempo_min": 60},
    ("incendio_vivienda", "alta"):  {"bomberos": 14, "agua_litros": 12000, "espuma_litros": 500,  "vehiculos": 4, "tiempo_min": 120},
    ("incendio_industrial", "baja"):  {"bomberos": 6,  "agua_litros": 5000,  "espuma_litros": 500,  "vehiculos": 2, "tiempo_min": 45},
    ("incendio_industrial", "media"): {"bomberos": 12, "agua_litros": 15000, "espuma_litros": 2000, "vehiculos": 4, "tiempo_min": 90},
    ("incendio_industrial", "alta"):  {"bomberos": 20, "agua_litros": 30000, "espuma_litros": 5000, "vehiculos": 6, "tiempo_min": 180},
    ("accidente_trafico", "baja"):  {"bomberos": 4, "agua_litros": 500,  "espuma_litros": 100,  "vehiculos": 2, "tiempo_min": 20},
    ("accidente_trafico", "media"): {"bomberos": 6, "agua_litros": 1000, "espuma_litros": 200,  "vehiculos": 3, "tiempo_min": 45},
    ("accidente_trafico", "alta"):  {"bomberos": 10, "agua_litros": 2000, "espuma_litros": 500, "vehiculos": 4, "tiempo_min": 90},
    ("rescate_altura", "baja"):  {"bomberos": 4,  "agua_litros": 0,    "espuma_litros": 0,   "vehiculos": 1, "tiempo_min": 30},
    ("rescate_altura", "media"): {"bomberos": 8,  "agua_litros": 500,  "espuma_litros": 0,   "vehiculos": 2, "tiempo_min": 60},
    ("rescate_altura", "alta"):  {"bomberos": 14, "agua_litros": 1000, "espuma_litros": 0,   "vehiculos": 4, "tiempo_min": 120},
    ("incendio_forestal", "baja"):  {"bomberos": 8,  "agua_litros": 8000,  "espuma_litros": 0,    "vehiculos": 2, "tiempo_min": 60},
    ("incendio_forestal", "media"): {"bomberos": 16, "agua_litros": 20000, "espuma_litros": 1000, "vehiculos": 5, "tiempo_min": 180},
    ("incendio_forestal", "alta"):  {"bomberos": 30, "agua_litros": 50000, "espuma_litros": 3000, "vehiculos": 8, "tiempo_min": 360},
    ("fuga_quimica", "baja"):  {"bomberos": 4,  "agua_litros": 1000, "espuma_litros": 500,  "vehiculos": 2, "tiempo_min": 30},
    ("fuga_quimica", "media"): {"bomberos": 8,  "agua_litros": 3000, "espuma_litros": 1500, "vehiculos": 3, "tiempo_min": 60},
    ("fuga_quimica", "alta"):  {"bomberos": 14, "agua_litros": 8000, "espuma_litros": 4000, "vehiculos": 5, "tiempo_min": 120},
}


# ── Encoding helpers ─────────────────────────────────────────────────────

_TYPE_ENCODING = {t: i for i, t in enumerate(INCIDENT_TYPES.keys())}
_SEV_ENCODING = {"baja": 0, "media": 1, "alta": 2}
_RESOURCE_KEYS = ["bomberos", "agua_litros", "espuma_litros", "vehiculos", "tiempo_min"]


# ── Generar datos sinteticos y entrenar modelo ───────────────────────────

def _generate_training_data(n=300, seed=42):
    """Genera datos de entrenamiento con variacion aleatoria sobre la tabla base."""
    rng = random.Random(seed)
    X, y = [], []

    types = list(INCIDENT_TYPES.keys())
    for _ in range(n):
        t = rng.choice(types)
        s = rng.choice(SEVERITIES)
        area = rng.uniform(20, 2000)

        base = _RESOURCE_TABLE[(t, s)]
        # Escalar por area (referencia: 200m2)
        area_factor = max(0.5, min(3.0, area / 200.0))

        X.append([_TYPE_ENCODING[t], _SEV_ENCODING[s], area])

        resources = []
        for key in _RESOURCE_KEYS:
            val = base[key] * area_factor * rng.uniform(0.8, 1.2)
            resources.append(int(round(val)))
        y.append(resources)

    return np.array(X), np.array(y)


_models = {}


def _train_models():
    global _models
    if not HAS_SKLEARN:
        return

    X, y = _generate_training_data()

    for i, key in enumerate(_RESOURCE_KEYS):
        clf = DecisionTreeRegressor(max_depth=8, random_state=42)
        clf.fit(X, y[:, i])
        _models[key] = clf


_train_models()


# ── API publica ──────────────────────────────────────────────────────────

def estimate(incident_type: str, severity: str = "media", area_m2: float = 200) -> dict:
    """Estima recursos necesarios para un incidente.

    Args:
        incident_type: Tipo de incidente (ver INCIDENT_TYPES)
        severity: baja, media, alta
        area_m2: Area afectada en metros cuadrados

    Returns:
        dict con bomberos, agua_litros, espuma_litros, vehiculos, tiempo_min
    """
    if incident_type not in INCIDENT_TYPES:
        return {"error": f"Tipo desconocido: {incident_type}", "tipos_validos": list(INCIDENT_TYPES.keys())}
    if severity not in SEVERITIES:
        return {"error": f"Severidad desconocida: {severity}", "severidades_validas": SEVERITIES}

    area_m2 = max(10, min(10000, area_m2))

    if HAS_SKLEARN and _models:
        X = np.array([[_TYPE_ENCODING[incident_type], _SEV_ENCODING[severity], area_m2]])
        result = {}
        for key in _RESOURCE_KEYS:
            pred = _models[key].predict(X)[0]
            result[key] = max(1, int(pred))
        method = "decision_tree"
    else:
        base = _RESOURCE_TABLE.get((incident_type, severity))
        if not base:
            base = _RESOURCE_TABLE[("incendio_vivienda", "media")]
        area_factor = max(0.5, min(3.0, area_m2 / 200.0))
        result = {k: max(1, int(v * area_factor)) for k, v in base.items()}
        method = "lookup_fallback"

    return {
        "incident_type": incident_type,
        "severity": severity,
        "area_m2": area_m2,
        "method": method,
        "resources": result,
        "description": INCIDENT_TYPES[incident_type]["description"],
    }


def get_incident_types() -> list:
    """Devuelve lista de tipos de incidente con descripcion."""
    return [
        {"type": t, "description": info["description"], "icon": info["icon"]}
        for t, info in INCIDENT_TYPES.items()
    ]
