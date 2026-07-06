import asyncio
import time
from app.services.pipeline_core.stage import PipelineStage
from app.services.pipeline_core.context import PipelineContext
from app.services.stream_manager import stream_manager

class StreamingStage(PipelineStage):
    """
    Broadcasts the final rendered frame to any connected WebSockets.
    """
    def __init__(self, main_loop: asyncio.AbstractEventLoop):
        self.main_loop = main_loop
        # Simple rolling FPS calculation
        self._last_time = time.time()
        self._frame_times = []

    def process(self, context: PipelineContext) -> PipelineContext:
        if not context.encoded_frame_b64:
            return context
            
        now = time.time()
        dt = now - self._last_time
        self._last_time = now
        
        if dt > 0:
            self._frame_times.append(1.0 / dt)
            if len(self._frame_times) > 30:
                self._frame_times.pop(0)
                
        fps = sum(self._frame_times) / len(self._frame_times) if self._frame_times else 0.0

        payload = {
            "camera_id": context.camera_id,
            "timestamp": context.timestamp,
            "fps": round(fps, 1),
            "violation_count": context.assessment.get("total_violations", 0),
            "frame": context.encoded_frame_b64
        }
        
        # Safely broadcast across threads
        asyncio.run_coroutine_threadsafe(
            stream_manager.broadcast(context.camera_id, payload), 
            self.main_loop
        )
        
        return context
