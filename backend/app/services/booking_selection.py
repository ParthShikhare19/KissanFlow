"""Shared booking selection logic.

Picks the booking a farmer's dashboard / IVR should talk about. The old
behaviour ("latest created") let a freshly-booked future slot hide the booking
the farmer was actually queued for, so selection is now priority based:

1. Any booking physically at the mandi right now: ARRIVED → IN_QUEUE → PROCESSING
2. The soonest upcoming BOOKED slot (today first, then future days)
3. The latest COMPLETED booking whose payment has NOT been paid yet, so the
   farmer keeps seeing "payment pending" until money lands
4. None — a fully settled cycle clears the dashboard back to "book a slot"
"""
from datetime import date
from typing import Optional
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.slot_booking import SlotBooking, BookingStatus
from app.models.transaction import Transaction, PaymentStatus

# Statuses that mean the farmer is mid-journey.
ACTIVE_STATUSES = [
    BookingStatus.PROCESSING,
    BookingStatus.IN_QUEUE,
    BookingStatus.ARRIVED,
]

# SQL ordering: PROCESSING (most advanced) → IN_QUEUE → ARRIVED.
_STAGE_PRIORITY = case(
    (SlotBooking.status == BookingStatus.PROCESSING, 0),
    (SlotBooking.status == BookingStatus.IN_QUEUE, 1),
    else_=2,
)


async def select_relevant_booking(
    db: AsyncSession,
    farmer_id,
    today: Optional[date] = None,
) -> Optional[SlotBooking]:
    """Return the booking currently most relevant to the farmer (or None)."""
    today = today or date.today()

    base_query = select(SlotBooking).where(SlotBooking.farmer_id == farmer_id)

    # 1. In-progress bookings: the most advanced stage wins (processing over
    #    queued over just-arrived), then earliest slot.
    result = await db.execute(
        base_query.where(SlotBooking.status.in_(ACTIVE_STATUSES))
        .order_by(_STAGE_PRIORITY, SlotBooking.slot_date.asc(), SlotBooking.created_at.asc())
        .limit(1)
    )
    booking = result.scalar_one_or_none()
    if booking:
        return booking

    # 2. Soonest upcoming booked slot (today or later).
    result = await db.execute(
        base_query.where(
            SlotBooking.status == BookingStatus.BOOKED,
            SlotBooking.slot_date >= today,
        )
        .order_by(SlotBooking.slot_date.asc(), SlotBooking.slot_start_time.asc())
        .limit(1)
    )
    booking = result.scalar_one_or_none()
    if booking:
        return booking

    # 3. Latest completed booking still awaiting payment.
    result = await db.execute(
        base_query
        .outerjoin(Transaction, Transaction.slot_booking_id == SlotBooking.id)
        .where(
            SlotBooking.status == BookingStatus.COMPLETED,
            (Transaction.payment_status == None)
            | (Transaction.payment_status != PaymentStatus.PAID),
        )
        .order_by(SlotBooking.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
