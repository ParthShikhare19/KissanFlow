"""Procurement Centres router."""
import uuid
from datetime import date, time, timedelta
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.procurement_centre import ProcurementCentre
from app.models.slot_booking import SlotBooking, BookingStatus
from app.schemas.centre import CentreResponse, CentreAvailability, SlotInfo
from app.schemas.common import APIResponse

router = APIRouter(tags=["centres"])


def _build_slots(daily_capacity: int, avg_minutes: int, booked_per_slot: dict) -> list[SlotInfo]:
    """Divide 9AM-5PM into slots of avg_minutes width and compute availability."""
    slots = []
    start_hour, end_hour = 9, 17
    total_minutes = (end_hour - start_hour) * 60
    total_slots = max(1, total_minutes // avg_minutes)
    per_slot_cap = max(1, daily_capacity // total_slots)

    current = time(start_hour, 0)
    for i in range(total_slots):
        start_dt = current
        minutes_elapsed = (i + 1) * avg_minutes
        end_h = start_hour + minutes_elapsed // 60
        end_m = minutes_elapsed % 60
        if end_h > end_hour:
            break
        end_dt = time(end_h, end_m)

        key = f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}"
        booked = booked_per_slot.get(key, 0)
        available = max(0, per_slot_cap - booked)

        slots.append(SlotInfo(
            start_time=start_dt.strftime("%H:%M"),
            end_time=end_dt.strftime("%H:%M"),
            booked=booked,
            capacity=per_slot_cap,
            available=available,
            availability_pct=round(available / per_slot_cap * 100, 1),
        ))
        current = end_dt

    return slots


@router.get("/", response_model=APIResponse[list[CentreResponse]])
async def list_centres(
    db: Annotated[AsyncSession, Depends(get_db)],
    district: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
):
    query = select(ProcurementCentre).where(ProcurementCentre.is_active == True)
    if district:
        query = query.where(ProcurementCentre.district.ilike(f"%{district}%"))
    if state:
        query = query.where(ProcurementCentre.state.ilike(f"%{state}%"))

    result = await db.execute(query.order_by(ProcurementCentre.name))
    centres = result.scalars().all()
    return APIResponse(success=True, data=[CentreResponse.model_validate(c) for c in centres])


@router.get("/{centre_id}", response_model=APIResponse[CentreResponse])
async def get_centre(
    centre_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(ProcurementCentre).where(ProcurementCentre.id == centre_id)
    )
    centre = result.scalar_one_or_none()
    if not centre:
        raise HTTPException(status_code=404, detail="Centre not found")
    return APIResponse(success=True, data=CentreResponse.model_validate(centre))


@router.get("/{centre_id}/availability", response_model=APIResponse[CentreAvailability])
async def get_centre_availability(
    centre_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    date_str: str = Query(alias="date", default=None),
):
    target_date = date.fromisoformat(date_str) if date_str else date.today()

    result = await db.execute(
        select(ProcurementCentre).where(ProcurementCentre.id == centre_id)
    )
    centre = result.scalar_one_or_none()
    if not centre:
        raise HTTPException(status_code=404, detail="Centre not found")

    count_result = await db.execute(
        select(func.count()).where(
            SlotBooking.centre_id == centre_id,
            SlotBooking.slot_date == target_date,
            SlotBooking.status != BookingStatus.CANCELLED,
        )
    )
    booked_count = count_result.scalar() or 0
    available = max(0, centre.daily_capacity - booked_count)

    # Build per-slot booking counts
    bookings_result = await db.execute(
        select(SlotBooking).where(
            SlotBooking.centre_id == centre_id,
            SlotBooking.slot_date == target_date,
            SlotBooking.status != BookingStatus.CANCELLED,
        )
    )
    bookings = bookings_result.scalars().all()
    booked_per_slot: dict[str, int] = {}
    for b in bookings:
        key = f"{b.slot_start_time.strftime('%H:%M')}-{b.slot_end_time.strftime('%H:%M')}"
        booked_per_slot[key] = booked_per_slot.get(key, 0) + 1

    slots = _build_slots(centre.daily_capacity, centre.avg_processing_time_minutes, booked_per_slot)

    return APIResponse(success=True, data=CentreAvailability(
        centre_id=centre_id,
        date=target_date.isoformat(),
        daily_capacity=centre.daily_capacity,
        booked_count=booked_count,
        available=available,
        availability_pct=round(available / centre.daily_capacity * 100, 1),
        slots=slots,
    ))


@router.get("/{centre_id}/slots", response_model=APIResponse[list[SlotInfo]])
async def get_centre_slots(
    centre_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    date_str: str = Query(alias="date", default=None),
):
    target_date = date.fromisoformat(date_str) if date_str else date.today()

    result = await db.execute(
        select(ProcurementCentre).where(ProcurementCentre.id == centre_id)
    )
    centre = result.scalar_one_or_none()
    if not centre:
        raise HTTPException(status_code=404, detail="Centre not found")

    bookings_result = await db.execute(
        select(SlotBooking).where(
            SlotBooking.centre_id == centre_id,
            SlotBooking.slot_date == target_date,
            SlotBooking.status != BookingStatus.CANCELLED,
        )
    )
    bookings = bookings_result.scalars().all()
    booked_per_slot: dict[str, int] = {}
    for b in bookings:
        key = f"{b.slot_start_time.strftime('%H:%M')}-{b.slot_end_time.strftime('%H:%M')}"
        booked_per_slot[key] = booked_per_slot.get(key, 0) + 1

    slots = _build_slots(centre.daily_capacity, centre.avg_processing_time_minutes, booked_per_slot)
    return APIResponse(success=True, data=slots)
