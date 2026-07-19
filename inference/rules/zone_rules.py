"""
SentinelOps — Zone-Based Intelligence Rules
===============================================
These rules are architecture-ready but return 0.0 by default since
the current YOLO model does not produce a 'person' class (only
safety_helmet and reflective_jacket).  They will activate automatically
once a model with person detection is loaded and zones are configured.
"""

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
        # Zone rules require a 'person' class and configured zone polygons.
        # Currently disabled — returns 0.0 (no violation).
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
        # Zone rules require a 'person' class.
        # Currently disabled — returns 0.0 (no violation).
        return 0.0
