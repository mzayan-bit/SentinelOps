from app.services.pipeline_core.stage import PipelineStage
from app.services.pipeline_core.context import PipelineContext
from inference.predictor import PredictionService
from app.services.observability import observability_engine

class InferenceStage(PipelineStage):
    """
    Executes YOLO model inference on the preprocessed frame.
    """
    def __init__(self):
        self.predictor = PredictionService()

    def process(self, context: PipelineContext) -> PipelineContext:
        if context.processed_frame is None:
            raise ValueError("InferenceStage requires a processed_frame")
            
        prediction = self.predictor.predict(context.processed_frame)
        context.detections = prediction.get("detections", [])
        
        # Enterprise Datadog Observability Hook
        latency_ms = prediction.get("inference_time_ms", 0.0)
        confidences = [d.get("confidence", 0.0) for d in context.detections]
        
        observability_engine.record_inference(
            camera_id=context.camera_id,
            latency_ms=latency_ms,
            confidences=confidences,
            detections_count=len(context.detections),
            tracking_count=0
        )
        
        return context
