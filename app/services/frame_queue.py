import time
import queue
import threading
import logging
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)

class CameraFrameQueue:
    """
    Manages an asynchronous, bounded frame queue for a single camera.
    Provides a background consumer thread and metrics tracking (FPS, drops).
    """
    def __init__(self, camera_id: str, max_size: int = 30, process_callback: Callable[[Any], None] = None):
        """
        Args:
            camera_id (str): Identifier for the camera.
            max_size (int): Maximum number of frames to keep in the queue.
            process_callback (Callable): Function to process popped frames.
        """
        self.camera_id = camera_id
        self.max_size = max_size
        self._queue = queue.Queue(maxsize=max_size)
        self._process_callback = process_callback
        
        # Metrics
        self._frames_processed = 0
        self._dropped_frames = 0
        self._start_time = 0.0
        self._fps = 0.0
        
        # Thread control
        self._stop_event = threading.Event()
        self._consumer_thread = None

    def start(self):
        """Starts the background consumer thread."""
        if self._consumer_thread is not None and self._consumer_thread.is_alive():
            logger.warning(f"Consumer thread for {self.camera_id} is already running.")
            return

        self._stop_event.clear()
        self._frames_processed = 0
        self._dropped_frames = 0
        self._start_time = time.time()
        
        self._consumer_thread = threading.Thread(
            target=self._consume_loop,
            name=f"CameraQueueConsumer-{self.camera_id}",
            daemon=True
        )
        self._consumer_thread.start()
        logger.info(f"Started frame queue consumer for camera {self.camera_id}")

    def stop(self):
        """Signals the consumer thread to stop and waits for it to exit."""
        if self._consumer_thread is None or not self._consumer_thread.is_alive():
            return
            
        self._stop_event.set()
        # Wake up the queue if it's blocking on get()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
            
        self._consumer_thread.join(timeout=2.0)
        logger.info(f"Stopped frame queue consumer for camera {self.camera_id}")

    def put_frame(self, frame: Any):
        """
        Puts a new frame into the queue. If the queue is full, implements
        a dropping strategy by removing the oldest frame.
        """
        if self._stop_event.is_set():
            return

        try:
            # If full, drop the oldest frame to make room
            if self._queue.full():
                try:
                    self._queue.get_nowait()
                    self._dropped_frames += 1
                except queue.Empty:
                    pass
            self._queue.put_nowait(frame)
        except queue.Full:
            # Race condition: queue filled up between full() check and put_nowait()
            self._dropped_frames += 1

    def _consume_loop(self):
        """Background loop reading from the queue and calling the callback."""
        while not self._stop_event.is_set():
            try:
                frame = self._queue.get(timeout=0.5)
                if frame is None:
                    # None is used to wake up the thread during stop()
                    continue
                    
                if self._process_callback:
                    try:
                        self._process_callback(frame)
                    except Exception as e:
                        logger.error(f"Error processing frame for camera {self.camera_id}: {e}")
                        
                self._frames_processed += 1
                self._update_fps()
                self._queue.task_done()
                
            except queue.Empty:
                continue

    def _update_fps(self):
        """Updates the running FPS calculation."""
        elapsed = time.time() - self._start_time
        if elapsed > 0:
            self._fps = self._frames_processed / elapsed

    def get_metrics(self) -> Dict[str, Any]:
        """Returns current operational metrics."""
        return {
            "camera_id": self.camera_id,
            "queue_size": self._queue.qsize(),
            "dropped_frames": self._dropped_frames,
            "fps": round(self._fps, 2),
            "total_processed": self._frames_processed
        }
