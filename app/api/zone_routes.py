from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.db.database import get_db
from schemas.zone import ZoneCreate, ZoneUpdate, ZoneResponse
from app.core.security import Role, get_current_user, require_role
from app.db.models import UserModel
from app.repositories.zone_repository import zone_repository

router = APIRouter(tags=["zones"])


@router.post("/cameras/{camera_id}/zones", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_zone(camera_id: uuid.UUID, zone_in: ZoneCreate, db: AsyncSession = Depends(get_db), user: UserModel = Depends(require_role(Role.SUPERVISOR))):
    if not await zone_repository.camera_exists(db, camera_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    return await zone_repository.create(db, camera_id, zone_in)


@router.get("/cameras/{camera_id}/zones", response_model=list[ZoneResponse])
async def list_zones(camera_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: UserModel = Depends(require_role(Role.VIEWER))):
    return await zone_repository.list_by_camera(db, camera_id)


@router.put("/zones/{zone_id}", response_model=ZoneResponse)
async def update_zone(zone_id: uuid.UUID, zone_in: ZoneUpdate, db: AsyncSession = Depends(get_db), user: UserModel = Depends(require_role(Role.SUPERVISOR))):
    zone = await zone_repository.get(db, zone_id)
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    return await zone_repository.update(db, zone, zone_in)


@router.delete("/zones/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(zone_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: UserModel = Depends(require_role(Role.SUPERVISOR))):
    zone = await zone_repository.get(db, zone_id)
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    await zone_repository.delete(db, zone)
