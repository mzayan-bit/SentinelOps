from typing import Dict, Any
from inference.rules.base_rule import BaseRule

class HelmetRule(BaseRule):
    @property
    def name(self) -> str: return "NO_HELMET"
    
    @property
    def priority(self) -> int: return 90
    
    @property
    def severity(self) -> str: return "HIGH"
    
    @property
    def cooldown_seconds(self) -> int: return 60
    
    @property
    def escalation_level(self) -> int: return 1
    
    @property
    def description(self) -> str: return "Person detected without a safety helmet."
    
    @property
    def recommendation(self) -> str: return "Ensure all personnel in active zones wear hard hats."

    def evaluate(self, track: Dict[str, Any], context: 'PipelineContext') -> float:
        # Check if the tracked object is a person
        if track.get("class_name") != "person":
            return 0.0
            
        # The YOLO detection metadata might contain nested PPE info if it's a composite model
        # Or we check overlapping bounding boxes of class 'helmet' from context.detections
        # For this logic, we'll assume context.detections has 'helmet' boxes, and we check if any overlap this track
        person_bbox = track["bbox"]
        
        for det in context.detections:
            if det["class_name"] == "helmet":
                h_bbox = det["bounding_box"]
                h_rect = (h_bbox["x_min"], h_bbox["y_min"], h_bbox["x_max"], h_bbox["y_max"])
                
                # Check for intersection. If helmet is inside or overlaps upper half of person
                if self._overlaps(person_bbox, h_rect):
                    return 0.0 # Safe! Helmet found.
                    
        # No helmet found, violation!
        return track.get("confidence", 0.7) # Return the confidence of the person detection

    def _overlaps(self, person_bbox, item_bbox):
        # A simple bounding box overlap check
        px1, py1, px2, py2 = person_bbox
        ix1, iy1, ix2, iy2 = item_bbox
        
        # Check if item is roughly in the upper area of the person
        if iy2 > py1 + (py2 - py1) * 0.5:
            return False
            
        xx1 = max(px1, ix1)
        yy1 = max(py1, iy1)
        xx2 = min(px2, ix2)
        yy2 = min(py2, iy2)
        
        w = max(0, xx2 - xx1)
        h = max(0, yy2 - yy1)
        
        if w * h > 0:
            return True
        return False

class VestRule(BaseRule):
    @property
    def name(self) -> str: return "NO_VEST"
    
    @property
    def priority(self) -> int: return 80
    
    @property
    def severity(self) -> str: return "MEDIUM"
    
    @property
    def cooldown_seconds(self) -> int: return 60
    
    @property
    def escalation_level(self) -> int: return 0
    
    @property
    def description(self) -> str: return "Person detected without a high-visibility vest."
    
    @property
    def recommendation(self) -> str: return "Verify high-visibility vests are worn on the floor."

    def evaluate(self, track: Dict[str, Any], context: 'PipelineContext') -> float:
        if track.get("class_name") != "person":
            return 0.0
            
        person_bbox = track["bbox"]
        
        for det in context.detections:
            if det["class_name"] == "vest":
                v_bbox = det["bounding_box"]
                v_rect = (v_bbox["x_min"], v_bbox["y_min"], v_bbox["x_max"], v_bbox["y_max"])
                
                if self._overlaps(person_bbox, v_rect):
                    return 0.0 # Safe!
                    
        return track.get("confidence", 0.7)

    def _overlaps(self, person_bbox, item_bbox):
        px1, py1, px2, py2 = person_bbox
        ix1, iy1, ix2, iy2 = item_bbox
        
        xx1 = max(px1, ix1)
        yy1 = max(py1, iy1)
        xx2 = min(px2, ix2)
        yy2 = min(py2, iy2)
        
        w = max(0, xx2 - xx1)
        h = max(0, yy2 - yy1)
        
        if w * h > 0:
            return True
        return False
