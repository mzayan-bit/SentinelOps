"""
SentinelOps — NLP Parser Tests
==============================
Validates heuristic natural language translation to SearchFilters.
"""

from datetime import datetime, timezone, timedelta
from app.services.nlp_parser import NLPEngine

def test_parse_yesterdays_helmet_violations():
    ref_time = datetime(2026, 6, 28, 12, 0, 0, tzinfo=timezone.utc)
    q = "show yesterday's helmet violations"
    filters = NLPEngine.parse(q, reference_time=ref_time)
    
    assert filters.alert_type == "No Helmet"
    assert filters.aggregate is False
    assert filters.camera_id is None
    
    # Yesterday is 2026-06-27 00:00:00 to 2026-06-28 00:00:00
    assert filters.start_date == datetime(2026, 6, 27, 0, 0, 0, tzinfo=timezone.utc)
    assert filters.end_date == datetime(2026, 6, 28, 0, 0, 0, tzinfo=timezone.utc)

def test_parse_top_cameras():
    q = "show top cameras with violations"
    filters = NLPEngine.parse(q)
    
    assert filters.aggregate is True
    assert filters.sort_by == "count_desc"
    assert filters.alert_type is None
    assert filters.camera_id is None

def test_parse_camera_number():
    q = "show incidents from camera 2"
    filters = NLPEngine.parse(q)
    
    assert filters.aggregate is False
    assert filters.camera_id == "camera 2"

def test_parse_camera_cam_abbreviation():
    q = "alerts from cam-01"
    filters = NLPEngine.parse(q)
    
    assert filters.camera_id == "camera 01"

def test_parse_multiple_entities():
    ref_time = datetime(2026, 6, 28, 12, 0, 0, tzinfo=timezone.utc)
    q = "show me last week's restricted zone breaches from cam alpha"
    filters = NLPEngine.parse(q, reference_time=ref_time)
    
    assert filters.alert_type == "Zone Violation"
    assert filters.camera_id == "camera alpha"
    assert filters.start_date == ref_time - timedelta(days=7)
    assert filters.end_date == ref_time
