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
        
        # 2. Check for PERSISTENT violations
        track_assessments = context.assessment.get("track_assessments", [])
        
        persistent_violations = []
        for ta in track_assessments:
            for v in ta.get("violations", []):
                if v["state"] == "PERSISTENT":
                    # Mark that we are alerting on this!
                    persistent_violations.append({
                        "track_id": ta["track_id"],
                        "rule_name": v["rule_name"],
                        "severity": v["severity"],
                        "confidence": v["confidence"]
                    })
        
        if persistent_violations:
            summary = ", ".join([f"{pv['rule_name']} (ID:{pv['track_id']})" for pv in persistent_violations])
            logger.warning(f"Persistent Violation(s) detected on {context.camera_id}: {summary}")
            
            # Map severity string to enum
            highest_sev = SeverityLevel.LOW
            sev_map = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
            for pv in persistent_violations:
                s = sev_map.get(pv["severity"], 1)
                if s > sev_map.get(highest_sev.name, 1):
                    # We need to map string to enum properly
                    if pv["severity"] == "CRITICAL":
                        highest_sev = SeverityLevel.CRITICAL
                    elif pv["severity"] == "HIGH":
                        highest_sev = SeverityLevel.HIGH
                    elif pv["severity"] == "MEDIUM":
                        highest_sev = SeverityLevel.MEDIUM
            
            # Log the incident in the DB / timeline
            incident = IncidentCreate(
                camera_id=context.camera_id,
                severity=highest_sev,
                description=f"Automated AI Alert: {summary}"
            )
            incident_service.log_incident(incident)
            
            # Trigger the event recorder to save the 20-second MP4 clip
            event_recorder.trigger_recording(context.camera_id, metadata={"persistent": persistent_violations})
            
            # Pass this downstream so Visualization can render an "ALERT RECORDING" banner
            context.assessment["is_recording"] = True
            
        return context
