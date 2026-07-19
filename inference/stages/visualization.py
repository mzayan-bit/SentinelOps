"""
SentinelOps — Professional Visualization Stage
=================================================
Clear, intuitive PPE compliance overlays:

- GREEN boxes on detected equipment (helmet ✓, vest ✓)
- RED "MISSING" zone drawn where the absent item SHOULD be
- Violation banner with clear text
- Clean labels with confidence scores
"""

import cv2
import base64
import time
import math
from app.services.pipeline_core.stage import PipelineStage
from app.services.pipeline_core.context import PipelineContext

# Color palette (BGR)
COLOR_COMPLIANT  = (0, 220, 0)       # Bright green — item is present
COLOR_VIOLATION  = (0, 0, 240)       # Red — item is missing
COLOR_WARNING_BG = (0, 0, 200)       # Dark red for violation banner background
COLOR_SAFE_BG    = (0, 140, 0)       # Dark green for safe banner background
COLOR_LABEL_BG   = (30, 30, 30)      # Dark background for labels
COLOR_WHITE      = (255, 255, 255)
COLOR_BLACK      = (0, 0, 0)
COLOR_ORANGE     = (0, 140, 255)     # Orange for NEW/ACTIVE warnings
COLOR_REC        = (0, 0, 255)       # Red for recording


def _draw_label(frame, text, x, y, bg_color, text_color=COLOR_WHITE, font_scale=0.5, thickness=1, padding=4):
    """Draw a text label with a filled background rectangle. Returns height used."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    cv2.rectangle(frame, (x, y - th - padding), (x + tw + padding * 2, y + padding), bg_color, -1)
    cv2.putText(frame, text, (x + padding, y), font, font_scale, text_color, thickness, cv2.LINE_AA)
    return th + padding * 2 + 2


def _draw_dashed_rect(frame, pt1, pt2, color, thickness=2, dash_length=10):
    """Draw a dashed rectangle."""
    x1, y1 = pt1
    x2, y2 = pt2
    # Top edge
    _draw_dashed_line(frame, (x1, y1), (x2, y1), color, thickness, dash_length)
    # Bottom edge
    _draw_dashed_line(frame, (x1, y2), (x2, y2), color, thickness, dash_length)
    # Left edge
    _draw_dashed_line(frame, (x1, y1), (x1, y2), color, thickness, dash_length)
    # Right edge
    _draw_dashed_line(frame, (x2, y1), (x2, y2), color, thickness, dash_length)


def _draw_dashed_line(frame, pt1, pt2, color, thickness=2, dash_length=10):
    """Draw a dashed line between two points."""
    x1, y1 = pt1
    x2, y2 = pt2
    dist = math.hypot(x2 - x1, y2 - y1)
    if dist == 0:
        return
    dx = (x2 - x1) / dist
    dy = (y2 - y1) / dist
    
    i = 0
    while i < dist:
        sx = int(x1 + dx * i)
        sy = int(y1 + dy * i)
        ex = int(x1 + dx * min(i + dash_length, dist))
        ey = int(y1 + dy * min(i + dash_length, dist))
        cv2.line(frame, (sx, sy), (ex, ey), color, thickness)
        i += dash_length * 2


class VisualizationStage(PipelineStage):
    """
    Draws clear, intuitive PPE compliance overlays:
    - Detected items → GREEN box
    - Missing items → RED dashed "ghost" box where item should be
    """
    def __init__(self, target_width: int = 1280):
        self.target_width = target_width
        
    def process(self, context: PipelineContext) -> PipelineContext:
        if context.processed_frame is None:
            return context
            
        frame = context.processed_frame.copy()
        h_frame, w_frame = frame.shape[:2]
        now = time.time()
        
        # Build violation lookup: track_id -> list of violations
        assessments_by_track = {}
        for ta in context.assessment.get("track_assessments", []):
            assessments_by_track[ta["track_id"]] = ta.get("violations", [])

        # ─── STEP 1: Draw ALL tracked objects in GREEN (they ARE detected) ───
        for track in context.tracks:
            bbox = track["bbox"]
            track_id = track["object_id"]
            cx, cy = track["centroid"]
            cls_name = track.get("class_name", "unknown")
            conf = track.get("confidence", 0.0)
            
            x1, y1 = int(bbox[0]), int(bbox[1])
            x2, y2 = int(bbox[2]), int(bbox[3])
            box_h = y2 - y1
            box_w = x2 - x1
            
            violations = assessments_by_track.get(track_id, [])
            active_violations = [v for v in violations 
                                 if v["state"] in ("ACTIVE", "PERSISTENT", "ALERTED")]
            
            # The DETECTED item is always GREEN — it exists!
            cv2.rectangle(frame, (x1, y1), (x2, y2), COLOR_COMPLIANT, 2)
            
            # Clean label: class name + confidence
            nice_name = "Helmet" if cls_name == "safety_helmet" else "Vest" if cls_name == "reflective_jacket" else cls_name
            label = f"{nice_name} [{conf:.0%}]"
            check_mark = "OK" if not active_violations else ""
            if check_mark:
                label = f"{nice_name} {check_mark} [{conf:.0%}]"
            _draw_label(frame, label, x1, y2 + 16, COLOR_SAFE_BG, COLOR_WHITE, 0.45, 1)
            
            # Centroid
            cv2.circle(frame, (cx, cy), 3, COLOR_WHITE, -1)
            
            # ─── STEP 2: For violations, draw the MISSING item as a RED ghost zone ───
            for v in active_violations:
                rule_name = v["rule_name"]
                duration = v.get("duration", 0)
                state = v["state"]
                
                # Determine where the MISSING item should be drawn
                if rule_name == "NO_VEST" and cls_name == "safety_helmet":
                    # Helmet is here, vest is MISSING → draw red zone BELOW the helmet (torso area)
                    vest_y1 = y2 + 5
                    vest_y2 = min(y2 + int(box_h * 4.0), h_frame - 5)
                    vest_x1 = max(x1 - int(box_w * 0.5), 0)
                    vest_x2 = min(x2 + int(box_w * 0.5), w_frame - 1)
                    
                    # Pulsing semi-transparent red overlay
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (vest_x1, vest_y1), (vest_x2, vest_y2), COLOR_VIOLATION, -1)
                    alpha = 0.15 + abs(math.sin(now * 3)) * 0.1
                    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
                    
                    # Dashed red border
                    _draw_dashed_rect(frame, (vest_x1, vest_y1), (vest_x2, vest_y2), COLOR_VIOLATION, 2, 8)
                    
                    # Violation banner in the middle of the ghost zone
                    banner_y = (vest_y1 + vest_y2) // 2
                    banner_text = f"MISSING VEST | {state} | {duration:.1f}s"
                    _draw_label(frame, banner_text, vest_x1, banner_y, COLOR_WARNING_BG, COLOR_WHITE, 0.55, 2)
                    
                elif rule_name == "NO_HELMET" and cls_name == "reflective_jacket":
                    # Vest is here, helmet is MISSING → draw red zone ABOVE the vest (head area)
                    helm_y2 = y1 - 5
                    helm_y1 = max(y1 - int(box_h * 0.6), 5)
                    helm_x_center = (x1 + x2) // 2
                    helm_half_w = int(box_w * 0.3)
                    helm_x1 = max(helm_x_center - helm_half_w, 0)
                    helm_x2 = min(helm_x_center + helm_half_w, w_frame - 1)
                    
                    # Pulsing semi-transparent red overlay
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (helm_x1, helm_y1), (helm_x2, helm_y2), COLOR_VIOLATION, -1)
                    alpha = 0.15 + abs(math.sin(now * 3)) * 0.1
                    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
                    
                    # Dashed red border
                    _draw_dashed_rect(frame, (helm_x1, helm_y1), (helm_x2, helm_y2), COLOR_VIOLATION, 2, 8)
                    
                    # Violation banner above the ghost zone
                    banner_text = f"MISSING HELMET | {state} | {duration:.1f}s"
                    _draw_label(frame, banner_text, helm_x1, helm_y1 - 2, COLOR_WARNING_BG, COLOR_WHITE, 0.55, 2)

        # ─── STEP 3: Draw non-tracked detections (duplicates from raw output) ───
        tracked_rects = set()
        for track in context.tracks:
            b = track["bbox"]
            tracked_rects.add((int(b[0]), int(b[1]), int(b[2]), int(b[3])))
        
        for det in context.detections:
            bbox = det["bounding_box"]
            dx1, dy1 = int(bbox["x_min"]), int(bbox["y_min"])
            dx2, dy2 = int(bbox["x_max"]), int(bbox["y_max"])
            
            # Skip if already drawn via tracker
            if (dx1, dy1, dx2, dy2) in tracked_rects:
                continue
            
            # Skip if very close to an already tracked rect (IoU-based dedup)
            skip = False
            for tr in tracked_rects:
                if _rects_overlap((dx1, dy1, dx2, dy2), tr):
                    skip = True
                    break
            if skip:
                continue
                
            cls = det["class_name"]
            conf = det["confidence"]
            nice = "Helmet" if cls == "safety_helmet" else "Vest" if cls == "reflective_jacket" else cls
            
            cv2.rectangle(frame, (dx1, dy1), (dx2, dy2), COLOR_COMPLIANT, 1)
            _draw_label(frame, f"{nice} [{conf:.0%}]", dx1, dy1 - 2, COLOR_LABEL_BG, COLOR_COMPLIANT, 0.4, 1)

        # ─── STEP 4: "REC" banner if alerting stage triggered ──────────
        if context.assessment.get("is_recording", False):
            pulse = abs(math.sin(now * 3))
            if pulse > 0.3:
                cv2.circle(frame, (25, 25), 10, COLOR_REC, -1)
                _draw_label(frame, "REC - AI VIOLATION ALERT", 42, 33, COLOR_REC, COLOR_WHITE, 0.6, 2)

        # ─── Encode frame to JPEG ─────────────────────────────────────
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        context.encoded_frame_b64 = base64.b64encode(buffer).decode('utf-8')
        
        return context


def _rects_overlap(a, b, threshold=0.4):
    """Check if two (x1,y1,x2,y2) rects overlap significantly."""
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    if area_a + area_b - inter <= 0:
        return False
    return inter / (area_a + area_b - inter) > threshold
