"""Pydantic schemas for SlotBooking."""
import uuid
from datetime import date, time, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.slot_booking import BookingStatus
from app.schemas.crop import CropResponse
from app.schemas.centre import CentreResponse
from app.schemas.user import UserResponse


class BookingCreate(BaseModel):
    centre_id: uuid.UUID
    crop_id: uuid.UUID
    preferred_date: date
    declared_quantity_q: float
    preferred_slot_start_time: Optional[time] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "centre_id": "uuid-here",
                "crop_id": "uuid-here",
                "preferred_date": "2025-01-15",
                "declared_quantity_q": 25.5,
            }
        }
    )


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    farmer_id: uuid.UUID
    centre_id: uuid.UUID
    crop_id: uuid.UUID
    slot_date: date
    slot_start_time: time
    slot_end_time: time
    token_number: str
    qr_code_data: str
    status: BookingStatus
    declared_quantity_q: float
    created_at: datetime

    # Optional nested objects
    crop: Optional[CropResponse] = None
    centre: Optional[CentreResponse] = None
    farmer: Optional[UserResponse] = None


class BookingWithQR(BookingResponse):
    qr_code_base64: Optional[str] = None
