from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseRule(ABC):
    """
    Abstract base class for all Video Intelligence Rules.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the rule (e.g., 'NO_HELMET')"""
        pass
        
    @property
    def priority(self) -> int:
        """Priority of the rule (higher overrides lower if mutually exclusive). Default 50."""
        return 50
        
    @property
    def severity(self) -> str:
        """Severity string (e.g., 'HIGH', 'MEDIUM', 'LOW')"""
        return "MEDIUM"
        
    @property
    def cooldown_seconds(self) -> int:
        """How many seconds before a resolved rule can trigger a new alert for the same track."""
        return 60
        
    @property
    def escalation_level(self) -> int:
        """Defines how urgently this should be escalated (0 = Log, 1 = Email, 2 = SMS/Siren)"""
        return 0
        
    @property
    @abstractmethod
    def description(self) -> str:
        """Human readable description of the violation"""
        pass
        
    @property
    @abstractmethod
    def recommendation(self) -> str:
        """Actionable recommendation for the operator"""
        pass

    @abstractmethod
    def evaluate(self, track: Dict[str, Any], context: 'PipelineContext') -> float:
        """
        Evaluate if the track is violating this rule.
        Returns a confidence score between 0.0 and 1.0.
        0.0 means no violation. >0.0 means violation with X confidence.
        """
        pass
