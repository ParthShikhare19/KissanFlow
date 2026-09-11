"""Pydantic schemas for QueueEntry."""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.queue_entry import QueueStatus


class GateEntryRequest(BaseModel):
    token_number: str | None = None
    booking_id: uuid.UUID | None = None


class QueueEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slot_booking_id: uuid.UUID
    centre_id: uuid.UUID
    position: int
    estimated_wait_minutes: int
    status: QueueStatus
    gate_entry_time: datetime

    # Enriched fields (set manually, not from DB)
    farmer_name: str | None = None
    token_number: str | None = None
    crop_name: str | None = None
    declared_quantity_q: float | None = None


class QueuePositionResponse(BaseModel):
    booking_id: uuid.UUID
    position: int
    estimated_wait_minutes: int
    status: QueueStatus
    ahead_of_you: int


class CallNextRequest(BaseModel):
    centre_id: uuid.UUID
