from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CameraModel, ZoneModel
from schemas.zone import ZoneCreate, ZoneUpdate


class ZoneRepository:
    async def camera_exists(self, db: AsyncSession, camera_id: uuid.UUID) -> bool:
        return await db.get(CameraModel, camera_id) is not None

    async def create(self, db: AsyncSession, camera_id: uuid.UUID, zone_in: ZoneCreate) -> ZoneModel:
        zone = ZoneModel(
            camera_id=camera_id,
            name=zone_in.name,
            points_json=zone_in.points_json,
            is_restricted=zone_in.is_restricted,
            max_dwell_time=zone_in.max_dwell_time,
        )
        db.add(zone)
        await db.commit()
        await db.refresh(zone)
        return zone

    async def list_by_camera(
        self,
        db: AsyncSession,
        camera_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ZoneModel]:
        result = await db.execute(
            select(ZoneModel)
            .where(ZoneModel.camera_id == camera_id)
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def get(self, db: AsyncSession, zone_id: uuid.UUID) -> ZoneModel | None:
        return await db.get(ZoneModel, zone_id)

    async def update(self, db: AsyncSession, zone: ZoneModel, zone_in: ZoneUpdate) -> ZoneModel:
        for key, value in zone_in.model_dump(exclude_unset=True).items():
            setattr(zone, key, value)

        await db.commit()
        await db.refresh(zone)
        return zone

    async def delete(self, db: AsyncSession, zone: ZoneModel) -> None:
        await db.delete(zone)
        await db.commit()


zone_repository = ZoneRepository()
