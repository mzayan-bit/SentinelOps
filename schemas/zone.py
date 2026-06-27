from __future__ import annotations

import uuid
from typing import List
from pydantic import BaseModel, Field

class ZoneBase(BaseModel):
    name: str = Field(..., max_length=255)
    points_json: str = Field(..., description="JSON string of [[x, y], ...]")
    is_restricted: bool = Field(default=False)
    max_dwell_time: int | None = Field(default=None, description="Seconds before alert")

class ZoneCreate(ZoneBase):
    pass

class ZoneUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    points_json: str | None = None
    is_restricted: bool | None = None
    max_dwell_time: int | None = None

class ZoneResponse(ZoneBase):
    id: uuid.UUID
    camera_id: uuid.UUID

    model_config = {"from_attributes": True}
