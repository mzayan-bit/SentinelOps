import pytest
import time
from schemas.incident import IncidentCreate, SeverityLevel
from app.services.incident_service import IncidentService

def test_log_incident():
    service = IncidentService()
    incident_data = IncidentCreate(
        camera_id="cam_01",
        severity=SeverityLevel.HIGH,
        description="Missing Helmet",
        screenshot_path="/data/screenshots/img1.jpg"
    )
    
    incident = service.log_incident(incident_data)
    
    assert incident.camera_id == "cam_01"
    assert incident.severity == SeverityLevel.HIGH
    assert incident.description == "Missing Helmet"
    assert incident.screenshot_path == "/data/screenshots/img1.jpg"
    assert incident.timestamp > 0
    assert len(service.get_incidents()) == 1

def test_get_incidents_filtering():
    service = IncidentService()
    service.log_incident(IncidentCreate(camera_id="cam_01", severity=SeverityLevel.LOW, description="A"))
    service.log_incident(IncidentCreate(camera_id="cam_02", severity=SeverityLevel.HIGH, description="B"))
    service.log_incident(IncidentCreate(camera_id="cam_01", severity=SeverityLevel.CRITICAL, description="C"))
    
    # Filter by camera_id
    cam1_incidents = service.get_incidents(camera_id="cam_01")
    assert len(cam1_incidents) == 2
    assert all(i.camera_id == "cam_01" for i in cam1_incidents)
    
    # Filter by severity
    high_incidents = service.get_incidents(severity=SeverityLevel.HIGH)
    assert len(high_incidents) == 1
    assert high_incidents[0].camera_id == "cam_02"

def test_get_incidents_time_range_and_sorting():
    service = IncidentService()
    
    start_time = time.time()
    service.log_incident(IncidentCreate(camera_id="cam_01", severity=SeverityLevel.LOW, description="A"))
    time.sleep(0.01)
    
    mid_time = time.time()
    service.log_incident(IncidentCreate(camera_id="cam_01", severity=SeverityLevel.MEDIUM, description="B"))
    time.sleep(0.01)
    end_time = time.time()
    
    # Fetch all, should be newest first
    all_incidents = service.get_incidents()
    assert all_incidents[0].description == "B"
    assert all_incidents[1].description == "A"
    
    # Time filter
    filtered = service.get_incidents(start_time=mid_time, end_time=end_time)
    assert len(filtered) == 1
    assert filtered[0].description == "B"

def test_get_incidents_limit():
    service = IncidentService()
    for i in range(5):
        service.log_incident(IncidentCreate(camera_id="cam_01", severity=SeverityLevel.LOW, description=str(i)))
        
    limited = service.get_incidents(limit=2)
    assert len(limited) == 2
