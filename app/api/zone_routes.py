from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.db.database import get_db
from app.db.models import ZoneModel, CameraModel
from schemas.zone import ZoneCreate, ZoneUpdate, ZoneResponse

router = APIRouter(tags=["zones"])


@router.post("/cameras/{camera_id}/zones", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_zone(camera_id: uuid.UUID, zone_in: ZoneCreate, db: AsyncSession = Depends(get_db)):
    # Check if camera exists
    camera = await db.get(CameraModel, camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")

    new_zone = ZoneModel(
        camera_id=camera_id,
        name=zone_in.name,
        points_json=zone_in.points_json,
        is_restricted=zone_in.is_restricted,
        max_dwell_time=zone_in.max_dwell_time,
    )
    db.add(new_zone)
    await db.commit()
    await db.refresh(new_zone)
    return new_zone


@router.get("/cameras/{camera_id}/zones", response_model=list[ZoneResponse])
async def list_zones(camera_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ZoneModel).where(ZoneModel.camera_id == camera_id))
    return result.scalars().all()


@router.put("/zones/{zone_id}", response_model=ZoneResponse)
async def update_zone(zone_id: uuid.UUID, zone_in: ZoneUpdate, db: AsyncSession = Depends(get_db)):
    zone = await db.get(ZoneModel, zone_id)
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")

    update_data = zone_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(zone, key, value)

    await db.commit()
    await db.refresh(zone)
    return zone


@router.delete("/zones/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(zone_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    zone = await db.get(ZoneModel, zone_id)
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")

    await db.delete(zone)
    await db.commit()
