"""WebSocket para streaming de estado en tiempo real."""

import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
from api.state import shared_state

router = APIRouter()


@router.websocket("/twin/{vehicle_id}/stream")
async def twin_stream(websocket: WebSocket, vehicle_id: str):
    """WebSocket que envía el estado del vehículo cada 2 segundos."""
    await websocket.accept()
    logger.info(f"WebSocket conectado para {vehicle_id}")

    try:
        while True:
            state = shared_state.get_state()
            if state and state.get("vehicle_id") == vehicle_id:
                await websocket.send_json(state)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        logger.info(f"WebSocket desconectado para {vehicle_id}")
    except Exception as e:
        logger.error(f"Error en WebSocket: {e}")
