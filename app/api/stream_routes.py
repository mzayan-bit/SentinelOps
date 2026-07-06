import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from app.services.stream_manager import stream_manager
from app.core.security import verify_token, Role

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Streaming"])

@router.websocket("/ws/stream/{camera_id}")
async def stream_camera(
    websocket: WebSocket,
    camera_id: str,
    token: str | None = Query(None, description="JWT token for authentication"),
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
    if token:
        try:
            payload = verify_token(token, "access")
            if not payload or payload.get("role") not in [r.value for r in Role]:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
        except Exception:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    else:
        # In a strict environment, close if no token is provided.
        pass

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
