from app.services.pipeline_core.stage import PipelineStage
from app.services.pipeline_core.context import PipelineContext
from inference.violation_engine import PPEViolationEngine

class ViolationStage(PipelineStage):
    """
    Applies business rules to the tracked detections to find violations.
    """
    def __init__(self):
        self.engine = PPEViolationEngine()

    def process(self, context: PipelineContext) -> PipelineContext:
        # Wrap detections in the format the old engine expected
        prediction_payload = {
            "detections": context.detections
        }
        
        assessment = self.engine.evaluate(prediction_payload)
        context.assessment = assessment
        
        return context
