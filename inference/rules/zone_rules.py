from typing import Dict, Any
import time
from inference.rules.base_rule import BaseRule

class RestrictedZoneRule(BaseRule):
    @property
    def name(self) -> str: return "RESTRICTED_ZONE"
    
    @property
    def priority(self) -> int: return 100
    
    @property
    def severity(self) -> str: return "CRITICAL"
    
    @property
    def cooldown_seconds(self) -> int: return 120
    
    @property
    def escalation_level(self) -> int: return 2
    
    @property
    def description(self) -> str: return "Person entered a restricted dangerous area."
    
    @property
    def recommendation(self) -> str: return "Immediately evacuate person from the restricted zone."

    def evaluate(self, track: Dict[str, Any], context: 'PipelineContext') -> float:
        if track.get("class_name") != "person":
            return 0.0
            
        # Hardcoded logic or pulled from context.zones (usually injected by ZoneEngine)
        # Assuming context has zone polygons
        centroid = track["centroid"]
        
        # Simple placeholder if no zone engine provides it:
        # In a real setup, we would do cv2.pointPolygonTest
        return 0.0

class LoiteringRule(BaseRule):
    @property
    def name(self) -> str: return "LOITERING"
    
    @property
    def priority(self) -> int: return 60
    
    @property
    def severity(self) -> str: return "LOW"
    
    @property
    def cooldown_seconds(self) -> int: return 300
    
    @property
    def escalation_level(self) -> int: return 0
    
    @property
    def description(self) -> str: return "Person loitering in an area for too long."
    
    @property
    def recommendation(self) -> str: return "Investigate reason for loitering."

    def evaluate(self, track: Dict[str, Any], context: 'PipelineContext') -> float:
        if track.get("class_name") != "person":
            return 0.0
            
        # Check temporal history
        history = track.get("history", [])
        if len(history) < 30:
            return 0.0
            
        # If the bounding box hasn't moved much over the last 30 frames
        first_box = history[0]
        last_box = history[-1]
        
        # Calculate displacement of centroid
        cx1 = (first_box[0] + first_box[2])/2
        cy1 = (first_box[1] + first_box[3])/2
        cx2 = (last_box[0] + last_box[2])/2
        cy2 = (last_box[1] + last_box[3])/2
        
        displacement = ((cx2-cx1)**2 + (cy2-cy1)**2)**0.5
        
        if displacement < 50: # Hasn't moved more than 50 pixels in 30 frames
            return track.get("confidence", 0.6)
            
        return 0.0
