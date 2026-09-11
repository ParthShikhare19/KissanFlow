"""Pydantic schemas for ProcurementCentre."""
import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict


class CentreCreate(BaseModel):
    name: str
    district: str
    state: str
    latitude: float = 0.0
    longitude: float = 0.0
    daily_capacity: int = 100
    avg_processing_time_minutes: int = 20
    is_active: bool = True


class CentreUpdate(BaseModel):
    name: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    daily_capacity: Optional[int] = None
    avg_processing_time_minutes: Optional[int] = None
    is_active: Optional[bool] = None


class CentreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    district: str
    state: str
    latitude: float
    longitude: float
    daily_capacity: int
    avg_processing_time_minutes: int
    is_active: bool


class SlotInfo(BaseModel):
    start_time: str
    end_time: str
    booked: int
    capacity: int
    available: int
    availability_pct: float


class CentreAvailability(BaseModel):
    centre_id: uuid.UUID
    date: str
    daily_capacity: int
    booked_count: int
    available: int
    availability_pct: float
    slots: list[SlotInfo]
