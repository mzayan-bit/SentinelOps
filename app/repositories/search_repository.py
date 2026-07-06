from __future__ import annotations

from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ViolationModel
from schemas.search import SearchFilters


class SearchRepository:
    def _apply_filters(self, stmt: Any, filters: SearchFilters) -> Any:
        if filters.camera_id:
            stmt = stmt.where(ViolationModel.camera_id == filters.camera_id)
        if filters.alert_type:
            stmt = stmt.where(ViolationModel.alert_type == filters.alert_type)
        if filters.start_date:
            stmt = stmt.where(ViolationModel.timestamp >= filters.start_date)
        if filters.end_date:
            stmt = stmt.where(ViolationModel.timestamp <= filters.end_date)
        return stmt

    async def aggregate_by_camera(self, db: AsyncSession, filters: SearchFilters) -> list[dict[str, Any]]:
        stmt = (
            select(
                ViolationModel.camera_id,
                func.count(ViolationModel.id).label("count"),
            )
            .group_by(ViolationModel.camera_id)
            .order_by(desc("count"))
        )
        stmt = self._apply_filters(stmt, filters)
        result = await db.execute(stmt)
        return [{"camera_id": row.camera_id, "count": row.count} for row in result.all()]

    async def list_violations(
        self,
        db: AsyncSession,
        filters: SearchFilters,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        stmt = self._apply_filters(select(ViolationModel), filters)
        stmt = stmt.order_by(ViolationModel.timestamp.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        return [
            {
                "id": violation.id,
                "camera_id": violation.camera_id,
                "alert_type": violation.alert_type,
                "timestamp": violation.timestamp.isoformat() if violation.timestamp else None,
                "severity": violation.severity,
            }
            for violation in result.scalars().all()
        ]


search_repository = SearchRepository()
