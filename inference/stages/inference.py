from app.services.pipeline_core.stage import PipelineStage
from app.services.pipeline_core.context import PipelineContext
from inference.predictor import PredictionService

class InferenceStage(PipelineStage):
    """
    Executes YOLO model inference on the preprocessed frame.
    """
    def __init__(self):
        self.predictor = PredictionService()

    def process(self, context: PipelineContext) -> PipelineContext:
        if context.processed_frame is None:
            raise ValueError("InferenceStage requires a processed_frame")
            
        # The predictor inherently scales internally to 640/1280 depending on the model, 
        # but bounding boxes are returned relative to the input shape.
        prediction = self.predictor.predict(context.processed_frame)
        context.detections = prediction.get("detections", [])
        
        return context
