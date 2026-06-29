"""
SentinelOps — Recommendation Engine Tests
=======================================
Validates the heuristic recommendation rules.
"""

from app.models.analytics import (
    AnalyticsSummaryResponse, 
    ComplianceRateResponse,
    TopViolationTypesResponse,
    ViolationTypeCount,
    ViolationsPerCameraResponse,
    ViolationsPerCamera,
    HourlyTrendsResponse,
    HourlyTrend,
    ViolationsPerDayResponse,
    ViolationsPerDay
)
from app.services.recommendation_engine import RecommendationEngine

def create_mock_summary(compliance_rate: float, top_type_count: int, top_cam_count: int) -> AnalyticsSummaryResponse:
    # Build a mock payload
    comp = ComplianceRateResponse(
        total_checks=100, 
        compliant=int(100*compliance_rate), 
        non_compliant=100-int(100*compliance_rate), 
        compliance_rate=compliance_rate
    )
    
    top_types = TopViolationTypesResponse(
        data=[ViolationTypeCount(violation_type="No Helmet", count=top_type_count)] if top_type_count else [],
        total=top_type_count
    )
    
    cams = ViolationsPerCameraResponse(
        data=[ViolationsPerCamera(camera_id="cam-01", count=top_cam_count)] if top_cam_count else [],
        total_cameras=1 if top_cam_count else 0
    )
    
    # 24 hours, set hour 14 as peak
    hour_data = [HourlyTrend(hour=h, count=10 if h == 14 else 1) for h in range(24)]
    hours = HourlyTrendsResponse(data=hour_data, date=None)
    
    days = ViolationsPerDayResponse(
        data=[ViolationsPerDay(date="2026-06-29", count=top_type_count)],
        total=top_type_count
    )
    
    return AnalyticsSummaryResponse(
        violations_per_day=days,
        violations_per_camera=cams,
        compliance_rate=comp,
        hourly_trends=hours,
        top_violation_types=top_types
    )

def test_critical_compliance():
    # 85% compliance -> HIGH priority rule
    summary = create_mock_summary(0.85, 0, 0)
    res = RecommendationEngine.generate_recommendations(summary)
    
    recs = res.recommendations
    assert len(recs) >= 1
    # Check compliance rule fired
    assert any(r.title == "Critical Compliance Drop" for r in recs)
    # Check priority sorting (HIGH should be first)
    assert recs[0].priority == "HIGH"

def test_improve_compliance_margin():
    # 96% compliance -> MEDIUM priority rule
    summary = create_mock_summary(0.96, 0, 0)
    res = RecommendationEngine.generate_recommendations(summary)
    
    assert any(r.title == "Improve Compliance Margin" for r in res.recommendations)

def test_top_violation_rule():
    # Perfect compliance but we have a top type issue (simulate isolated incidents)
    summary = create_mock_summary(1.0, 15, 0)
    res = RecommendationEngine.generate_recommendations(summary)
    
    assert any(r.title == "Address Top Violation: No Helmet" for r in res.recommendations)

def test_camera_hotspot_rule():
    summary = create_mock_summary(1.0, 0, 20)
    res = RecommendationEngine.generate_recommendations(summary)
    
    assert any(r.title == "Targeted Patrols Needed" for r in res.recommendations)

def test_peak_hour_rule():
    # Our mock always sets hour 14 to peak
    summary = create_mock_summary(1.0, 0, 0)
    res = RecommendationEngine.generate_recommendations(summary)
    
    assert any(r.title == "Optimize Supervisor Scheduling" for r in res.recommendations)
    # Check the hour is formatted
    assert any("14:00" in r.description for r in res.recommendations)

def test_default_all_clear():
    # Zero everything, 100% compliance
    comp = ComplianceRateResponse(total_checks=100, compliant=100, non_compliant=0, compliance_rate=1.0)
    top_types = TopViolationTypesResponse(data=[], total=0)
    cams = ViolationsPerCameraResponse(data=[], total_cameras=0)
    hours = HourlyTrendsResponse(data=[], date=None)
    days = ViolationsPerDayResponse(data=[], total=0)
    
    summary = AnalyticsSummaryResponse(
        violations_per_day=days,
        violations_per_camera=cams,
        compliance_rate=comp,
        hourly_trends=hours,
        top_violation_types=top_types
    )
    
    res = RecommendationEngine.generate_recommendations(summary)
    assert len(res.recommendations) == 1
    assert res.recommendations[0].title == "Maintain Current Protocols"
