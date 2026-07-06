import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from app.services.stream_manager import stream_manager
from app.auth import _AUTH_ENABLED, _user_store, Role

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Streaming"])

@router.websocket("/ws/stream/{camera_id}")
async def stream_camera(
    websocket: WebSocket,
    camera_id: str,
    api_key: str | None = Query(None, description="API Key for authentication"),
):
    """
    WebSocket endpoint for real-time video streaming.
    
    The payload sent to clients will include:
    - encoded frame (base64 or bytes string)
    - detections (bounding boxes, classes)
    - fps
    - violation count
    - timestamps
    """
    import app.auth
    if app.auth._AUTH_ENABLED:
        key = api_key or websocket.headers.get("x-api-key")
        if not key:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        user = _user_store.authenticate(key)
        if not user or user.role < Role.VIEWER:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    await stream_manager.connect(websocket, camera_id)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
                continue

            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await stream_manager.disconnect(websocket, camera_id)
    except Exception as e:
        logger.exception("WebSocket error on stream %s: %s", camera_id, e)
        await stream_manager.disconnect(websocket, camera_id)
