"""
SentinelOps — Search Routes
===========================
Natural language search API endpoints.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.repositories.search_repository import search_repository
from app.services.nlp_parser import NLPEngine
from schemas.search import SearchResponse
from app.core.security import Role, get_current_user, require_role, User

router = APIRouter(prefix="/api/search", tags=["search"])

@router.get("", response_model=SearchResponse)
async def search_incidents(
    q: str = Query(..., description="Natural language query string"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.VIEWER))
):
    """
    Parse a natural language query into database filters and return matching incidents.
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty")
        
    filters = NLPEngine.parse(q)

    if filters.aggregate:
        results_list = await search_repository.aggregate_by_camera(db, filters)
    else:
        results_list = await search_repository.list_violations(
            db,
            filters,
            limit=filters.limit or 100,
        )

    return SearchResponse(
        query=q,
        filters=filters,
        results=results_list,
        count=len(results_list)
    )
