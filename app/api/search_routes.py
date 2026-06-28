"""
SentinelOps — Search Routes
===========================
Natural language search API endpoints.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.db.database import get_db
from app.db.models import ViolationModel
from app.services.nlp_parser import NLPEngine
from schemas.search import SearchResponse

router = APIRouter(prefix="/api/search", tags=["search"])

@router.get("", response_model=SearchResponse)
async def search_incidents(
    q: str = Query(..., description="Natural language query string"),
    db: AsyncSession = Depends(get_db)
):
    """
    Parse a natural language query into database filters and return matching incidents.
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty")
        
    # 1. Translate NL to Filters
    filters = NLPEngine.parse(q)
    
    # 2. Build SQLAlchemy Query
    stmt = select(ViolationModel)
    
    if filters.camera_id:
        stmt = stmt.where(ViolationModel.camera_id == filters.camera_id)
        
    if filters.alert_type:
        stmt = stmt.where(ViolationModel.alert_type == filters.alert_type)
        
    if filters.start_date:
        stmt = stmt.where(ViolationModel.timestamp >= filters.start_date)
        
    if filters.end_date:
        stmt = stmt.where(ViolationModel.timestamp <= filters.end_date)
        
    # 3. Handle Intent (Aggregation vs List)
    if filters.aggregate:
        # e.g., "top cameras" -> Group by camera_id and count
        agg_stmt = (
            select(
                ViolationModel.camera_id, 
                func.count(ViolationModel.id).label("count")
            )
            .group_by(ViolationModel.camera_id)
            .order_by(desc("count"))
        )
        
        # Apply the same WHERE clauses to the aggregation
        if filters.alert_type:
            agg_stmt = agg_stmt.where(ViolationModel.alert_type == filters.alert_type)
        if filters.start_date:
            agg_stmt = agg_stmt.where(ViolationModel.timestamp >= filters.start_date)
        if filters.end_date:
            agg_stmt = agg_stmt.where(ViolationModel.timestamp <= filters.end_date)
            
        result = await db.execute(agg_stmt)
        rows = result.all()
        
        results_list = [{"camera_id": r.camera_id, "count": r.count} for r in rows]
        
    else:
        # Standard list
        stmt = stmt.order_by(ViolationModel.timestamp.desc())
        if filters.limit:
            stmt = stmt.limit(filters.limit)
        else:
            stmt = stmt.limit(100)  # Safe default limit
            
        result = await db.execute(stmt)
        violations = result.scalars().all()
        results_list = [
            {
                "id": v.id,
                "camera_id": v.camera_id,
                "alert_type": v.alert_type,
                "timestamp": v.timestamp.isoformat() if v.timestamp else None,
                "severity": v.severity
            } 
            for v in violations
        ]

    return SearchResponse(
        query=q,
        filters=filters,
        results=results_list,
        count=len(results_list)
    )
