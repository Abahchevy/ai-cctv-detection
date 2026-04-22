"""
Pydantic schemas for API responses.
"""
from __future__ import annotations

import json
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class CameraOut(BaseModel):
    id: str
    name: str
    source: str
    zone_id: str
    enabled: bool
    running: bool


class CameraCreate(BaseModel):
    id: str
    name: str
    source: str
    enabled: bool = True


class CameraStatusUpdate(BaseModel):
    enabled: bool


class CameraUpdate(BaseModel):
    name: str
    source: str
    enabled: bool


class ViolationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: str
    zone_id: str
    track_id: Optional[int]
    missing_ppe: list[str]
    snapshot_path: Optional[str]
    timestamp_utc: str
    frame_index: int

    @field_validator("missing_ppe", mode="before")
    @classmethod
    def parse_missing_ppe(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
