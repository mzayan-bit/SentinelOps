import cv2
from app.services.pipeline_core.stage import PipelineStage
from app.services.pipeline_core.context import PipelineContext

class PreprocessingStage(PipelineStage):
    """
    Validates and resizes the raw input frame.
    We resize early so that inference, tracking, and visualization all operate on the same scaled coordinate space.
    """
    def __init__(self, max_width: int = 1280):
        self.max_width = max_width

    def process(self, context: PipelineContext) -> PipelineContext:
        frame = context.original_frame
        if frame is None or frame.size == 0:
            raise ValueError("Empty or invalid frame")
            
        h, w = frame.shape[:2]
        
        # Keep original frame reference for debugging if needed, but set processed_frame to scaled
        if w > self.max_width:
            scale = self.max_width / w
            context.processed_frame = cv2.resize(frame, (self.max_width, int(h * scale)))
        else:
            # We must copy to ensure downstream stages don't mutate the raw pointer if it's shared
            context.processed_frame = frame.copy()
            
        return context
