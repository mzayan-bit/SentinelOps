import logging
from app.services.pipeline_core.stage import PipelineStage
from app.services.pipeline_core.context import PipelineContext
from app.services.event_recorder import event_recorder
from app.services.incident_service import incident_service
from schemas.incident import IncidentCreate, SeverityLevel

logger = logging.getLogger("sentinelops.alerting_stage")

class AlertingStage(PipelineStage):
    """
    Triggers DB logging and video recording clips when rules are broken.
    """
    def process(self, context: PipelineContext) -> PipelineContext:
        # 1. Always push the frame into the circular buffer
        event_recorder.push_frame(context.camera_id, context.original_frame)
        
        # 2. Check for violations
        total_violations = context.assessment.get("total_violations", 0)
        
        if total_violations > 0:
            logger.warning(f"Violation detected on {context.camera_id}: {context.assessment.get('summary')}")
            
            # Log the incident in the DB / timeline
            incident = IncidentCreate(
                camera_id=context.camera_id,
                severity=SeverityLevel.HIGH,
                description=str(context.assessment.get("summary", "Unknown violation"))
            )
            incident_service.log_incident(incident)
            
            # Trigger the event recorder to save the 20-second MP4 clip
            event_recorder.trigger_recording(context.camera_id, metadata=context.assessment)
            
        return context
