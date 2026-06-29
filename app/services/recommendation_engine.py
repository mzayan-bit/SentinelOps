"""
SentinelOps — Recommendation Engine
=====================================
A heuristic engine that analyzes macro-level analytics summaries
to generate structured, data-driven safety recommendations.
"""

from typing import List
from app.models.analytics import AnalyticsSummaryResponse, Recommendation, RecommendationResponse

class RecommendationEngine:
    """Heuristic engine to analyze site-wide safety telemetry."""

    @classmethod
    def generate_recommendations(cls, summary: AnalyticsSummaryResponse) -> RecommendationResponse:
        """
        Analyze the full analytics payload and return prioritized recommendations.
        """
        recs: List[Recommendation] = []
        
        # 1. Compliance Statistics
        comp_data = summary.compliance_rate
        if comp_data.total_checks > 0:
            if comp_data.compliance_rate < 0.90:
                recs.append(Recommendation(
                    title="Critical Compliance Drop",
                    description=f"Overall PPE compliance has dropped to {comp_data.compliance_rate * 100:.1f}%. Immediate site-wide safety stand-down is recommended to review basic PPE requirements.",
                    priority="HIGH",
                    category="Compliance"
                ))
            elif comp_data.compliance_rate < 0.98:
                recs.append(Recommendation(
                    title="Improve Compliance Margin",
                    description=f"Compliance is at {comp_data.compliance_rate * 100:.1f}%. Consider verbal reminders during the next shift briefing to push back above 98%.",
                    priority="MEDIUM",
                    category="Compliance"
                ))

        # 2. Repeated Violations (Top Types)
        top_types = summary.top_violation_types.data
        if top_types:
            top_issue = top_types[0]
            if top_issue.count > 0:
                recs.append(Recommendation(
                    title=f"Address Top Violation: {top_issue.violation_type}",
                    description=f"'{top_issue.violation_type}' accounts for {top_issue.count} recent incidents. Audit inventory, signage, and distribution specific to this PPE type.",
                    priority="HIGH",
                    category="Equipment"
                ))

        # 3. Location/Camera Hotspots
        cams = summary.violations_per_camera.data
        if cams:
            worst_cam = cams[0]
            if worst_cam.count > 0:
                # If one camera has disproportionately more, flag it
                recs.append(Recommendation(
                    title=f"Targeted Patrols Needed",
                    description=f"Camera '{worst_cam.camera_id}' recorded the highest volume of incidents ({worst_cam.count}). Deploy a safety supervisor to this specific area to identify systemic hazards.",
                    priority="MEDIUM",
                    category="Location"
                ))

        # 4. Hourly Trends (Peak Times)
        hours = summary.hourly_trends.data
        if hours:
            # Find the hour with the maximum count
            peak_hour = max(hours, key=lambda x: x.count)
            if peak_hour.count > 0:
                recs.append(Recommendation(
                    title="Optimize Supervisor Scheduling",
                    description=f"Peak violations consistently occur around {peak_hour.hour:02d}:00 ({peak_hour.count} incidents). Schedule active supervisor floor-walks during this time window.",
                    priority="MEDIUM",
                    category="Time"
                ))
                
        # 5. Default "All Clear"
        if not recs:
            recs.append(Recommendation(
                title="Maintain Current Protocols",
                description="No critical anomalies detected in recent telemetry. Continue standard operating procedures.",
                priority="LOW",
                category="Compliance"
            ))

        # Sort recommendations: HIGH -> MEDIUM -> LOW
        priority_map = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        recs.sort(key=lambda r: priority_map.get(r.priority, 99))

        return RecommendationResponse(recommendations=recs)
