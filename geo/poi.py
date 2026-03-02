"""
Carga POIs (Points of Interest) desde archivos JSON estáticos.
Hidrantes y estaciones de bomberos de Valencia.
"""

import json
import os
from loguru import logger

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _load_json(filename: str) -> list[dict]:
    path = os.path.join(_DATA_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error cargando {filename}: {e}")
        return []


def load_hydrants() -> list[dict]:
    """Carga posiciones de hidrantes de Valencia."""
    return _load_json("hydrants.json")


def load_stations() -> list[dict]:
    """Carga estaciones de bomberos de Valencia."""
    return _load_json("stations.json")
