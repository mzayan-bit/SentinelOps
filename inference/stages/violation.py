import time
from enum import Enum
from typing import Dict, Any
from app.services.pipeline_core.stage import PipelineStage
from app.services.pipeline_core.context import PipelineContext
from inference.rules.ppe_rules import HelmetRule, VestRule
from inference.rules.zone_rules import RestrictedZoneRule, LoiteringRule

class LifecycleState(Enum):
    NEW = "NEW"
    ACTIVE = "ACTIVE"
    PERSISTENT = "PERSISTENT"
    ALERTED = "ALERTED"
    RESOLVED = "RESOLVED"
    EXPIRED = "EXPIRED"

class ViolationManager:
    def __init__(self, persistent_threshold_seconds=2.0):
        self.rules = [HelmetRule(), VestRule(), RestrictedZoneRule(), LoiteringRule()]
        self.persistent_threshold = persistent_threshold_seconds
        
        # State: track_id -> { rule_name -> { state: LifecycleState, first_seen: float, last_seen: float, last_alerted: float, confidence: float } }
        self.state = {}

    def evaluate(self, tracks: list, context: PipelineContext) -> list:
        now = time.time()
        active_track_ids = set()
        
        # Output assessments to attach to context for visualization
        assessments = []

        for track in tracks:
            track_id = track["object_id"]
            active_track_ids.add(track_id)
            
            if track_id not in self.state:
                self.state[track_id] = {}
                
            track_violations = []

            for rule in self.rules:
                rule_name = rule.name
                
                # evaluate() returns a confidence score > 0 if violated
                confidence = rule.evaluate(track, context)
                
                is_violating = confidence > 0.0
                
                if rule_name not in self.state[track_id]:
                    self.state[track_id][rule_name] = {
                        "state": LifecycleState.EXPIRED,
                        "first_seen": 0,
                        "last_seen": 0,
                        "last_alerted": 0,
                        "confidence": 0.0
                    }
                    
                v_state = self.state[track_id][rule_name]
                
                if is_violating:
                    v_state["last_seen"] = now
                    v_state["confidence"] = confidence
                    
                    if v_state["state"] in (LifecycleState.EXPIRED, LifecycleState.RESOLVED):
                        # Transition to NEW
                        if now - v_state["last_alerted"] < rule.cooldown_seconds:
                            continue
                            
                        v_state["state"] = LifecycleState.NEW
                        v_state["first_seen"] = now
                    elif v_state["state"] == LifecycleState.NEW:
                        # Transition to ACTIVE immediately if seen again
                        v_state["state"] = LifecycleState.ACTIVE
                    elif v_state["state"] == LifecycleState.ACTIVE:
                        # Check temporal persistence
                        if now - v_state["first_seen"] >= self.persistent_threshold:
                            # Trigger alert
                            v_state["state"] = LifecycleState.PERSISTENT
                            v_state["last_alerted"] = now
                    elif v_state["state"] == LifecycleState.PERSISTENT:
                        # Transition immediately to ALERTED so it doesn't fire again
                        v_state["state"] = LifecycleState.ALERTED
                        
                    # Add to current frame violations
                    track_violations.append({
                        "rule_name": rule.name,
                        "severity": rule.severity,
                        "state": v_state["state"].value,
                        "confidence": v_state["confidence"],
                        "duration": now - v_state["first_seen"]
                    })
                else:
                    # Not violating
                    if v_state["state"] in (LifecycleState.NEW, LifecycleState.ACTIVE, LifecycleState.PERSISTENT, LifecycleState.ALERTED):
                        # Give it a 1-second grace period before resolving to prevent flickering
                        if now - v_state["last_seen"] > 1.0:
                            v_state["state"] = LifecycleState.RESOLVED
                            
            if track_violations:
                assessments.append({
                    "track_id": track_id,
                    "violations": track_violations,
                    "centroid": track["centroid"],
                    "bbox": track["bbox"]
                })
                
        # Clean up expired tracks
        for tid in list(self.state.keys()):
            if tid not in active_track_ids:
                # Mark all active violations as resolved if object disappeared
                for rname, v_state in self.state[tid].items():
                    if v_state["state"] in (LifecycleState.NEW, LifecycleState.ACTIVE, LifecycleState.PERSISTENT, LifecycleState.ALERTED):
                        v_state["state"] = LifecycleState.RESOLVED
                    elif v_state["state"] == LifecycleState.RESOLVED:
                        if now - v_state["last_seen"] > max(r.cooldown_seconds for r in self.rules):
                            v_state["state"] = LifecycleState.EXPIRED
                            
                # If all expired, remove the track state
                if all(s["state"] == LifecycleState.EXPIRED for s in self.state[tid].values()):
                    del self.state[tid]

        return assessments


class ViolationStage(PipelineStage):
    """
    Applies modular business rules to the tracked detections.
    Maintains a temporal state machine for alert lifecycle.
    """
    def __init__(self):
        self.manager = ViolationManager()

    def process(self, context: PipelineContext) -> PipelineContext:
        assessments = self.manager.evaluate(context.tracks, context)
        context.assessment = {"track_assessments": assessments}
        return context
