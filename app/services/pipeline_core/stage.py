from abc import ABC, abstractmethod
from app.services.pipeline_core.context import PipelineContext
import time

class PipelineStage(ABC):
    """
    Abstract base class for a single step in the AI Inference Pipeline.
    """
    
    @property
    def name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Execute this stage's business logic, modifying the context.
        """
        pass
        
    def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Wrapper to execute the stage and record performance telemetry.
        """
        start = time.perf_counter()
        
        try:
            result = self.process(context)
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            context.record_metric(self.name, duration_ms)
            
        return result
