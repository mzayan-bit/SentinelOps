import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.stream_manager import stream_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Streaming"])

@router.websocket("/ws/stream/{camera_id}")
async def stream_camera(websocket: WebSocket, camera_id: str):
    """
    WebSocket endpoint for real-time video streaming.
    
    The payload sent to clients will include:
    - encoded frame (base64 or bytes string)
    - detections (bounding boxes, classes)
    - fps
    - violation count
    - timestamps
    """
    await stream_manager.connect(websocket, camera_id)
    try:
        while True:
            # Keep connection alive; wait for client messages if they send commands
            # Mostly, clients just listen to the broadcasted frames.
            data = await websocket.receive_text()
            # Handle incoming client messages if necessary (e.g., ping)
    except WebSocketDisconnect:
        stream_manager.disconnect(websocket, camera_id)
    except Exception as e:
        logger.error(f"WebSocket error on stream {camera_id}: {e}")
        stream_manager.disconnect(websocket, camera_id)
