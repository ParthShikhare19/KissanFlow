"""Pydantic schemas for Dashboard and Analytics endpoints."""
import uuid
from typing import Optional
from pydantic import BaseModel


# ─── Mandi Dashboard ──────────────────────────────────────────────────────────

class MandiDashboard(BaseModel):
    centre_id: uuid.UUID
    centre_name: str
    date: str
    daily_capacity: int
    total_bookings: int
    arrived_count: int
    completed_count: int
    current_queue_size: int
    avg_processing_time_minutes: int
    quality_pending_count: int
    payment_pending_count: int
    active_grievances_count: int
    hourly_throughput: list[dict]


# ─── Govt Dashboard ───────────────────────────────────────────────────────────

class GovtDashboard(BaseModel):
    total_farmers: int
    total_procurement_q: float
    completed_q: float
    pending_q: float
    active_mandis: int
    high_congestion_count: int
    quality_delay_count: int
    payment_delay_count: int
    open_grievances: int


class DrilldownRow(BaseModel):
    id: Optional[uuid.UUID] = None
    name: str
    total_farmers: int
    procurement_q: float
    completed_pct: float
    congestion_status: str  # "normal" | "moderate" | "high"


class AnomalyFlag(BaseModel):
    centre_id: uuid.UUID
    centre_name: str
    district: str
    today_rejection_rate: float
    rolling_avg_rate: float
    severity: str
    created_at: str


# ─── Analytics ────────────────────────────────────────────────────────────────

class CongestionPrediction(BaseModel):
    centre_id: uuid.UUID
    date: str
    predicted_bookings: int
    daily_capacity: int
    predicted_occupancy_pct: float
    risk_level: str  # "low" | "moderate" | "high" | "critical"
