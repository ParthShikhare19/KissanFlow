"""Pydantic schemas for Crop."""
import uuid
from pydantic import BaseModel, ConfigDict
from app.models.crop import CropSeason


class CropCreate(BaseModel):
    name: str
    season: CropSeason
    msp_per_quintal: float
    crop_code: str


class CropUpdate(BaseModel):
    name: str | None = None
    season: CropSeason | None = None
    msp_per_quintal: float | None = None


class CropResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    season: CropSeason
    msp_per_quintal: float
    crop_code: str
