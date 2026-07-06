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
        
        # We will draw based on tracks now instead of raw detections, because the Rule Engine
        # evaluates tracks.
        
        # Build a lookup for assessments by track_id
        assessments_by_track = {}
        for ta in context.assessment.get("track_assessments", []):
            assessments_by_track[ta["track_id"]] = ta.get("violations", [])
            
        for track in context.tracks:
            bbox = track["bbox"]
            track_id = track["object_id"]
            cx, cy = track["centroid"]
            cls_name = track.get("class_name", "unknown")
            
            x1, y1 = int(bbox[0]), int(bbox[1])
            x2, y2 = int(bbox[2]), int(bbox[3])
            
            violations = assessments_by_track.get(track_id, [])
            
            is_violating = any(v["state"] in ("ACTIVE", "PERSISTENT", "ALERTED") for v in violations)
            
            color = COLOR_DANGER if is_violating else COLOR_SAFE
            
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw Tracking ID
            label = f"ID: {track_id} | {cls_name}"
            cv2.putText(frame, label, (x1, max(y1 - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Draw Violations
            y_offset = y1 - 30
            for v in violations:
                if v["state"] in ("ACTIVE", "PERSISTENT", "ALERTED", "NEW"):
                    v_text = f"{v['rule_name']} ({v['state']} {v['duration']:.1f}s) Conf:{v['confidence']:.2f}"
                    v_color = COLOR_DANGER if v["state"] in ("PERSISTENT", "ALERTED") else (0, 165, 255) # Orange for NEW/ACTIVE
                    cv2.putText(frame, v_text, (x1, max(y_offset, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, v_color, 2)
                    y_offset -= 20
                    
            # Draw Centroid
            cv2.circle(frame, (cx, cy), 4, (255, 255, 255), -1)

        # Draw generic detections that aren't tracked (e.g. helmets, vests) just for debug visualization
        for det in context.detections:
            if det["class_name"] != "person":
                bbox = det["bounding_box"]
                x1, y1 = int(bbox["x_min"]), int(bbox["y_min"])
                x2, y2 = int(bbox["x_max"]), int(bbox["y_max"])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 1) # Cyan for items
                cv2.putText(frame, det["class_name"], (x1, max(y1 - 5, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

        # Draw "RECORDING" banner if alerting stage triggered
        if context.assessment.get("is_recording", False):
            cv2.putText(frame, "REC - AI ALERT", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
            cv2.circle(frame, (30, 40), 10, (0, 0, 255), -1)

        # Encode frame to JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        context.encoded_frame_b64 = base64.b64encode(buffer).decode('utf-8')
        
        return context
