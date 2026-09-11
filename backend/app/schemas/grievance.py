"""Pydantic schemas for Grievance."""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.grievance import GrievanceCategory, GrievanceStatus


class GrievanceCreate(BaseModel):
    slot_booking_id: Optional[uuid.UUID] = None
    category: GrievanceCategory
    description: str


class GrievanceUpdate(BaseModel):
    status: Optional[GrievanceStatus] = None
    description: Optional[str] = None


class GrievanceAssign(BaseModel):
    assigned_to: uuid.UUID


class GrievanceResolve(BaseModel):
    resolution: str


class GrievanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    farmer_id: uuid.UUID
    slot_booking_id: Optional[uuid.UUID] = None
    category: GrievanceCategory
    description: str
    status: GrievanceStatus
    assigned_to: Optional[uuid.UUID] = None
    resolution: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    farmer_name: Optional[str] = None
    assigned_officer_name: Optional[str] = None
