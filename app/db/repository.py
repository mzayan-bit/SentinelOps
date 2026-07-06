"""
SentinelOps — Generic Repository Layer
========================================
Implements common CRUD operations using generic types to prevent
boilerplate duplication across business domains.
"""

from typing import Any, Generic, Sequence, Type, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

# Type Variables for Generic typing
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Generic repository providing standard CRUD operations.
    """

    def __init__(self, model: Type[ModelType]):
        """
        Args:
            model: The SQLAlchemy declarative model class this repository manages.
        """
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> ModelType | None:
        """Fetch a single record by primary key."""
        return await db.get(self.model, id)

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_desc: bool = False,
    ) -> Sequence[ModelType]:
        """Fetch multiple records with pagination."""
        stmt = select(self.model)
        if sort_by and hasattr(self.model, sort_by):
            column = getattr(self.model, sort_by)
            stmt = stmt.order_by(column.desc() if sort_desc else column.asc())
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def count(self, db: AsyncSession) -> int:
        """Count all records for this repository's model."""
        result = await db.execute(select(func.count()).select_from(self.model))
        return int(result.scalar_one())

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType | dict[str, Any]) -> ModelType:
        """Create a new record."""
        obj_in_data = obj_in.model_dump() if isinstance(obj_in, BaseModel) else obj_in
        db_obj = self.model(**obj_in_data)  # type: ignore
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any]
    ) -> ModelType:
        """Update an existing record."""
        obj_data = db_obj.__dict__
        update_data = obj_in.model_dump(exclude_unset=True) if isinstance(obj_in, BaseModel) else obj_in
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
                
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: Any) -> ModelType | None:
        """Delete a record by primary key."""
        obj = await db.get(self.model, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj
