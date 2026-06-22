import logging
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

    async def connect(self, websocket: WebSocket, camera_id: str):
        """Accepts a new WebSocket connection and adds it to the camera's pool."""
        await websocket.accept()
        if camera_id not in self.active_connections:
            self.active_connections[camera_id] = []
        self.active_connections[camera_id].append(websocket)
        logger.info(f"Client connected to camera {camera_id}. Total: {len(self.active_connections[camera_id])}")

    def disconnect(self, websocket: WebSocket, camera_id: str):
        """Removes a disconnected WebSocket from the camera's pool."""
        if camera_id in self.active_connections:
            if websocket in self.active_connections[camera_id]:
                self.active_connections[camera_id].remove(websocket)
            
            if not self.active_connections[camera_id]:
                del self.active_connections[camera_id]
            
            logger.info(f"Client disconnected from camera {camera_id}.")

    async def broadcast(self, camera_id: str, payload: Dict[str, Any]):
        """
        Broadcasts the given payload (frame, detections, etc.) to all connected clients
        for the specified camera_id.
        """
        if camera_id in self.active_connections:
            disconnected_clients = []
            
            for connection in self.active_connections[camera_id]:
                try:
                    await connection.send_json(payload)
                except Exception as e:
                    logger.warning(f"Failed to send to client on {camera_id}: {e}")
                    disconnected_clients.append(connection)
            
            # Clean up broken pipes
            for dead_conn in disconnected_clients:
                self.disconnect(dead_conn, camera_id)

stream_manager = StreamConnectionManager()
