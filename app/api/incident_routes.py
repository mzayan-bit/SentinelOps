from fastapi import APIRouter, Query, status
from typing import List, Optional
from schemas.incident import IncidentCreate, IncidentResponse, SeverityLevel
from app.services.incident_service import incident_service

router = APIRouter(prefix="/api/incidents", tags=["Incidents"])

@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED, summary="Log a new violation incident")
def create_incident(incident_in: IncidentCreate):
    """
    Logs a new violation event to the timeline. 
    Typically called by the model inference pipeline upon detecting a PPE violation.
    """
    return incident_service.log_incident(incident_in)

@router.get("", response_model=List[IncidentResponse], summary="Retrieve incidents with filters")
def get_incidents(
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    severity: Optional[SeverityLevel] = Query(None, description="Filter by severity level"),
    start_time: Optional[float] = Query(None, description="Start timestamp filter"),
    end_time: Optional[float] = Query(None, description="End timestamp filter"),
    limit: int = Query(100, description="Max number of incidents to return")
):
    """
    Retrieves the incident timeline. Supports filtering by camera, severity, and timestamp ranges.
    Results are automatically sorted newest-first.
    """
    return incident_service.get_incidents(
        camera_id=camera_id, 
        severity=severity, 
        start_time=start_time, 
        end_time=end_time, 
        limit=limit
    )
