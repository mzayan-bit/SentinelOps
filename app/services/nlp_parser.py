"""
SentinelOps — Natural Language Parser
=====================================
Heuristic-based NLP translation layer.
Translates human-readable queries into structured SearchFilters.
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from schemas.search import SearchFilters

class NLPEngine:
    """Heuristic rule-based natural language parser."""

    # Alert Type mappings (keyword -> canonical DB value)
    ALERT_TYPE_MAP = {
        "helmet": "No Helmet",
        "hard hat": "No Helmet",
        "vest": "No High-Vis Vest",
        "hi-vis": "No High-Vis Vest",
        "high-vis": "No High-Vis Vest",
        "glasses": "No Safety Glasses",
        "goggles": "No Safety Glasses",
        "restricted": "Zone Violation",
        "zone": "Zone Violation",
        "breach": "Zone Violation"
    }

    @classmethod
    def parse(cls, query: str, reference_time: Optional[datetime] = None) -> SearchFilters:
        """
        Parse a natural language query into structured database filters.
        
        Parameters
        ----------
        query : str
            The conversational search query.
        reference_time : datetime, optional
            The base time to use for relative time parsing (useful for tests).
            Defaults to current UTC time.
            
        Returns
        -------
        SearchFilters
            Pydantic model containing translated filter arguments.
        """
        q_lower = query.lower().strip()
        now = reference_time or datetime.now(timezone.utc)
        filters = SearchFilters()
        
        # 1. Intent Detection
        if re.search(r'\b(top|most|frequent|aggregate)\b', q_lower):
            filters.aggregate = True
            filters.sort_by = "count_desc"
            
        # 2. Date/Time Extraction
        filters.start_date, filters.end_date = cls._extract_dates(q_lower, now)
            
        # 3. Alert Type Extraction
        filters.alert_type = cls._extract_alert_type(q_lower)
        
        # 4. Camera Extraction
        # Look for phrases like "camera 2", "cam 2", "cam-02"
        # We use a non-capturing group and word boundary to avoid matching "cameras" -> "cam" + "eras"
        cam_match = re.search(r'\b(?:cam|camera)\b\s*[-_]?\s*([0-9a-z]+)\b', q_lower)
        if cam_match:
            # We preserve the raw matched identifier (e.g. "2", "01", "alpha")
            filters.camera_id = f"camera {cam_match.group(1)}"
            
        return filters

    @classmethod
    def _extract_dates(cls, q: str, now: datetime) -> tuple[Optional[datetime], Optional[datetime]]:
        """Parse relative date expressions."""
        start_date = None
        end_date = None
        
        # Midnight today
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if "yesterday" in q:
            start_date = today_start - timedelta(days=1)
            end_date = today_start
        elif "today" in q:
            start_date = today_start
            end_date = now
        elif "past 24 hours" in q or "last 24 hours" in q:
            start_date = now - timedelta(hours=24)
            end_date = now
        elif "past week" in q or "last week" in q:
            start_date = now - timedelta(days=7)
            end_date = now
            
        return start_date, end_date

    @classmethod
    def _extract_alert_type(cls, q: str) -> Optional[str]:
        """Map keywords to canonical alert types."""
        for keyword, canonical in cls.ALERT_TYPE_MAP.items():
            if re.search(r'\b' + re.escape(keyword) + r'\b', q):
                return canonical
        return None
