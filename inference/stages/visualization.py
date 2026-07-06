import cv2
import base64
from app.services.pipeline_core.stage import PipelineStage
from app.services.pipeline_core.context import PipelineContext

COLOR_SAFE = (0, 255, 0)
COLOR_DANGER = (0, 0, 255)

class VisualizationStage(PipelineStage):
    """
    Draws bounding boxes and overlays onto the frame, then encodes it for web streaming.
    """
    def __init__(self, target_width: int = 1280):
        self.target_width = target_width
        
    def process(self, context: PipelineContext) -> PipelineContext:
        if context.processed_frame is None:
            return context
            
        frame = context.processed_frame.copy()
        
        # Draw PPE detections
        for det in context.detections:
            bbox = det["bounding_box"]
            cls_name = det["class_name"]
            
            x1, y1 = int(bbox["x_min"]), int(bbox["y_min"])
            x2, y2 = int(bbox["x_max"]), int(bbox["y_max"])
            
            color = (0, 255, 255) if "vest" in cls_name.lower() or "jacket" in cls_name.lower() else COLOR_SAFE
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, cls_name, (x1, max(y1 - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
        # Draw violation outlines
        for v in context.assessment.get("violations", []):
            if v["status"] != "SAFE":
                bbox = v["person_bbox"]
                x1, y1 = int(bbox["x_min"]), int(bbox["y_min"])
                x2, y2 = int(bbox["x_max"]), int(bbox["y_max"])
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), COLOR_DANGER, 3)
                cv2.putText(frame, f"VIOLATION: {v['status']}", (x1, max(y1 - 25, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_DANGER, 2)

        # Draw Tracking IDs (Centroids)
        for track in context.tracks:
            cx, cy = track["centroid"]
            text = f"ID {track['object_id']}"
            cv2.putText(frame, text, (cx - 10, cy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            cv2.circle(frame, (cx, cy), 4, (255, 255, 255), -1)

        # Encode frame to JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        context.encoded_frame_b64 = base64.b64encode(buffer).decode('utf-8')
        
        return context
