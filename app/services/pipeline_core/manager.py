import logging
from typing import List
from app.services.pipeline_core.context import PipelineContext
from app.services.pipeline_core.stage import PipelineStage

logger = logging.getLogger("sentinelops.pipeline")

class PipelineManager:
    """
    Orchestrates the sequential execution of PipelineStages.
    Handles error recovery and prevents a failing stage from crashing the camera loop.
    """
    def __init__(self, stages: List[PipelineStage]):
        self.stages = stages
        
    def add_stage(self, stage: PipelineStage):
        self.stages.append(stage)

    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Runs the context through all configured stages.
        """
        for stage in self.stages:
            try:
                context = stage.execute(context)
            except Exception as e:
                logger.exception(f"Pipeline Stage '{stage.name}' failed for camera {context.camera_id}: {e}")
                # We do not re-raise. We want the stream to gracefully degrade (e.g. drop inference but keep streaming)
                # Certain critical stages might choose to flag the context as invalid, but the manager pushes through.
                break
                
        self._log_metrics(context)
        return context
        
    def _log_metrics(self, context: PipelineContext):
        total_time = sum(context.metrics.values())
        metrics_str = ", ".join([f"{k}: {v:.1f}ms" for k, v in context.metrics.items()])
        logger.debug(f"[Pipeline - {context.camera_id}] Total: {total_time:.1f}ms | {metrics_str}")
