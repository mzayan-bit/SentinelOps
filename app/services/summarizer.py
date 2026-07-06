"""
SentinelOps — Incident Summarizer
===================================
A template-based heuristic engine for generating human-readable
incident summaries with actionable safety recommendations.
"""

from datetime import datetime, timezone
import logging
from typing import Dict, Any

from schemas.incident import IncidentResponse

logger = logging.getLogger("sentinelops.summarizer")

class IncidentSummarizer:
    """Generates structured summaries for incidents based on heuristics."""

    # Map keywords found in incident descriptions to standard recommendations
    RECOMMENDATION_MAP = {
        "helmet": [
            "Remind worker of site-wide hard hat policies.",
            "Verify hard hat signage is visible at the entrance to this area.",
            "Ensure extra hard hats are available at the site office."
        ],
        "vest": [
            "Issue a verbal reminder regarding high-visibility clothing.",
            "Check lighting conditions in the area to ensure workers are visible.",
            "Review vest distribution log to ensure all workers are equipped."
        ],
        "glasses": [
            "Ensure safety goggles are provided before entry.",
            "Remind workers of eye-protection hazards in this zone."
        ],
        "zone": [
            "Review restricted area access logs.",
            "Consider adding physical barriers or warning tape to the zone perimeter.",
            "Verify that dwell-time limits are clearly communicated."
        ],
        "default": [
            "Conduct a brief safety stand-down to discuss this event.",
            "Review camera placement to ensure clear visibility of future incidents."
        ]
    }

    @classmethod
    def generate_summary(cls, incident: IncidentResponse) -> Dict[str, Any]:
        """
        Produce a structured summary dictionary from an incident.
        
        Parameters
        ----------
        incident : IncidentResponse
            The incident to summarize.
            
        Returns
        -------
        Dict[str, Any]
            The generated summary containing 'what', 'when', 'where', 'severity', and 'recommendations'.
        """
        # 1. When
        dt = datetime.fromtimestamp(incident.timestamp, tz=timezone.utc)
        when_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # 2. What
        what_str = f"A safety incident was logged: {incident.description}."
        
        # 3. Where
        where_str = f"Camera ID: {incident.camera_id}"
        
        # 4. Severity
        severity_str = incident.severity.upper()
        
        # 5. Recommendations (Heuristic Keyword Matching)
        desc_lower = incident.description.lower()
        recommendations = []
        
        for keyword, recs in cls.RECOMMENDATION_MAP.items():
            if keyword != "default" and keyword in desc_lower:
                recommendations.extend(recs)
                
        if not recommendations:
            recommendations.extend(cls.RECOMMENDATION_MAP["default"])
            
        # Optional Context based on severity
        if severity_str == "CRITICAL":
            recommendations.insert(0, "IMMEDIATE ACTION REQUIRED: Halt work in the affected area.")
            
        summary_text = (
            f"Incident Summary:\n"
            f"- What: {what_str}\n"
            f"- When: {when_str}\n"
            f"- Where: {where_str}\n"
            f"- Severity: {severity_str}\n\n"
            f"Actionable Recommendations:\n"
        )
        for i, rec in enumerate(recommendations, 1):
            summary_text += f"{i}. {rec}\n"

        return {
            "summary": summary_text.strip(),
            "what": what_str,
            "when": when_str,
            "where": where_str,
            "severity": severity_str,
            "recommendations": recommendations,
            "related_events_count": 0
        }
