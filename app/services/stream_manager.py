import logging
import asyncio
from typing import Dict, List, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class StreamConnectionManager:
    """
    Manages active WebSocket connections per camera ID.
    Supports multi-client broadcasting without blocking the inference pipeline.
    """
    def __init__(self):
        # Map of camera_id -> list of active websockets
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, camera_id: str):
        """Accepts a new WebSocket connection and adds it to the camera's pool."""
        await websocket.accept()
        async with self._lock:
            connections = self.active_connections.setdefault(camera_id, [])
            if websocket not in connections:
                connections.append(websocket)
            total = len(connections)
        logger.info("Client connected to camera %s. Total: %s", camera_id, total)

    async def disconnect(self, websocket: WebSocket, camera_id: str):
        """Removes a disconnected WebSocket from the camera's pool."""
        async with self._lock:
            if camera_id in self.active_connections:
                if websocket in self.active_connections[camera_id]:
                    self.active_connections[camera_id].remove(websocket)

                if not self.active_connections[camera_id]:
                    del self.active_connections[camera_id]

        logger.info("Client disconnected from camera %s.", camera_id)

    async def broadcast(self, camera_id: str, payload: Dict[str, Any]):
        """
        Broadcasts the given payload (frame, detections, etc.) to all connected clients
        for the specified camera_id.
        """
        async with self._lock:
            connections = list(self.active_connections.get(camera_id, []))

        disconnected_clients = []
        for connection in connections:
            try:
                await connection.send_json(payload)
            except Exception as e:
                logger.warning("Failed to send to client on %s: %s", camera_id, e)
                disconnected_clients.append(connection)

        for dead_conn in disconnected_clients:
            await self.disconnect(dead_conn, camera_id)

stream_manager = StreamConnectionManager()
