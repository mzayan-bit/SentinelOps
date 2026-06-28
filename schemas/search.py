"""
SentinelOps — Search Schemas
============================
Pydantic schemas for the NLP incident search functionality.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any

class SearchFilters(BaseModel):
    """Structured database filters translated from natural language."""
    camera_id: Optional[str] = None
    alert_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Intent tracking
    aggregate: bool = False
    sort_by: Optional[str] = None
    limit: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

class SearchResponse(BaseModel):
    """Response wrapper for search results."""
    query: str
    filters: SearchFilters
    results: List[Any]  # Can be ViolationResponse or aggregated data
    count: int
