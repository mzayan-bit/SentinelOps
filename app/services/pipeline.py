import logging
from typing import Tuple, Any, Dict
from inference.predictor import PredictionService
from inference.violation_engine import PPEViolationEngine
from app.services.event_recorder import event_recorder
from app.services.incident_service import incident_service
from schemas.incident import IncidentCreate, SeverityLevel

logger = logging.getLogger(__name__)

class InferencePipeline:
    """
    Demonstrates how the standalone CV engine integrates with the backend services.
    This acts as the main processing loop per camera.
    """
    def __init__(self):
        self.predictor = PredictionService()
        self.engine = PPEViolationEngine()

    def process_frame(self, camera_id: str, frame: Any) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Main pipeline hook. Processes a raw frame from a camera stream.
        Returns the prediction dict and the assessment dict.
        """
        # 1. Always push frame to continuous event recorder buffer
        event_recorder.push_frame(camera_id, frame)
        
        # 2. Run object detection
        prediction = self.predictor.predict(frame)
        
        # 3. Apply business rules
        assessment = self.engine.evaluate(prediction)
        
        # 4. Handle violations if found
        if assessment["total_violations"] > 0:
            logger.warning(f"Violation detected on {camera_id}: {assessment['summary']}")
            
            # Log the incident in the DB / timeline
            incident = IncidentCreate(
                camera_id=camera_id,
                severity=SeverityLevel.HIGH,
                description=str(assessment["summary"])
            )
            incident_service.log_incident(incident)
            
            # Trigger the event recorder to save the 20-second MP4 clip
            event_recorder.trigger_recording(camera_id, metadata=assessment)

        return prediction, assessment
