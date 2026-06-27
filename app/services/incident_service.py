import uuid
import time
import logging
from typing import List, Optional
from schemas.incident import IncidentCreate, IncidentResponse, SeverityLevel

logger = logging.getLogger(__name__)

class IncidentService:
    """
    Manages the central incident timeline. Stores violations and provides
    comprehensive filtering capabilities.
    """
    def __init__(self):
        # In-memory store for incidents. In production, this would be a DB layer.
        self._incidents: List[IncidentResponse] = []

    def log_incident(self, incident_in: IncidentCreate) -> IncidentResponse:
        """Logs a new violation event to the timeline."""
        incident = IncidentResponse(
            id=uuid.uuid4(),
            camera_id=incident_in.camera_id,
            severity=incident_in.severity,
            description=incident_in.description,
            screenshot_path=incident_in.screenshot_path,
            timestamp=time.time()
        )
        self._incidents.append(incident)
        logger.info(f"Logged incident {incident.id} for camera {incident.camera_id} with severity {incident.severity}")

        # Fire-and-forget: send Slack summary
        from app.services.slack_service import slack_service
        from app.services.task_worker import task_worker
        task_worker.submit(
            slack_service.send_incident_summary,
            incident,
            task_type="slack_incident_summary"
        )

        # Fire-and-forget: send Teams summary
        from app.services.teams_service import teams_service
        task_worker.submit(
            teams_service.send_incident_summary,
            incident,
            task_type="teams_incident_summary"
        )

        return incident

    def get_incidents(
        self, 
        camera_id: Optional[str] = None, 
        severity: Optional[SeverityLevel] = None, 
        start_time: Optional[float] = None, 
        end_time: Optional[float] = None,
        limit: int = 100
    ) -> List[IncidentResponse]:
        """
        Retrieves a filtered and sorted list of incidents.
        Sorts descending by timestamp (newest first).
        """
        filtered = self._incidents

        if camera_id:
            filtered = [i for i in filtered if i.camera_id == camera_id]
        if severity:
            filtered = [i for i in filtered if i.severity == severity]
        if start_time is not None:
            filtered = [i for i in filtered if i.timestamp >= start_time]
        if end_time is not None:
            filtered = [i for i in filtered if i.timestamp <= end_time]

        # Sort by timestamp descending (newest first)
        filtered.sort(key=lambda x: x.timestamp, reverse=True)
        return filtered[:limit]

    def clear_incidents(self):
        """Clears all incidents. Primarily used for testing."""
        self._incidents.clear()

incident_service = IncidentService()
