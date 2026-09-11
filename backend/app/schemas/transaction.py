"""Pydantic schemas for Transaction."""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.transaction import QualityStatus, ProcurementStatus, PaymentStatus


class TransactionCreate(BaseModel):
    slot_booking_id: uuid.UUID


class QualityUpdate(BaseModel):
    moisture_percent: float = Field(ge=0, le=100)
    foreign_matter_percent: float = Field(ge=0, le=100)
    quality_status: QualityStatus
    quality_notes: Optional[str] = None
    quality_photo_url: Optional[str] = None


class WeighmentUpdate(BaseModel):
    gross_weight_q: float = Field(gt=0)
    tare_weight_q: float = Field(ge=0)
    weighment_photo_url: Optional[str] = None

    @model_validator(mode="after")
    def tare_must_be_less_than_gross(self):
        if self.tare_weight_q >= self.gross_weight_q:
            raise ValueError("Tare weight must be less than gross weight")
        return self


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slot_booking_id: uuid.UUID
    farmer_id: uuid.UUID
    centre_id: uuid.UUID
    crop_id: uuid.UUID
    gross_weight_q: Optional[float] = None
    tare_weight_q: Optional[float] = None
    net_weight_q: Optional[float] = None
    msp_per_q: Optional[float] = None
    total_amount: Optional[float] = None
    quality_status: Optional[QualityStatus] = None
    moisture_percent: Optional[float] = None
    foreign_matter_percent: Optional[float] = None
    quality_notes: Optional[str] = None
    quality_photo_url: Optional[str] = None
    weighment_photo_url: Optional[str] = None
    procurement_status: ProcurementStatus
    payment_status: PaymentStatus
    payment_ref: Optional[str] = None
    pfms_transaction_id: Optional[str] = None
    staff_id: Optional[uuid.UUID] = None
    completed_at: Optional[datetime] = None
    quality_done_at: Optional[datetime] = None
    weighment_done_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    payment_initiated_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_at: datetime

    # Enriched fields
    farmer_name: Optional[str] = None
    crop_name: Optional[str] = None
    centre_name: Optional[str] = None
