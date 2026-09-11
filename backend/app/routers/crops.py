"""Crops router."""
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.crop import Crop
from app.schemas.crop import CropResponse
from app.schemas.common import APIResponse
from app.middleware.auth import CurrentUser

router = APIRouter(tags=["crops"])


@router.get("/", response_model=APIResponse[list[CropResponse]])
async def list_crops(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Crop).order_by(Crop.name))
    crops = result.scalars().all()
    return APIResponse(success=True, data=[CropResponse.model_validate(c) for c in crops])


@router.get("/{crop_id}", response_model=APIResponse[CropResponse])
async def get_crop(
    crop_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Crop).where(Crop.id == crop_id))
    crop = result.scalar_one_or_none()
    if not crop:
        raise HTTPException(status_code=404, detail="Crop not found")
    return APIResponse(success=True, data=CropResponse.model_validate(crop))
