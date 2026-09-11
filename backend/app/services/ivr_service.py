"""
IVR service — DB lookups used by Twilio webhook handlers.
"""
from typing import Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.slot_booking import SlotBooking, BookingStatus
from app.models.queue_entry import QueueEntry
from app.models.grievance import Grievance, GrievanceCategory, GrievanceStatus
from app.models.crop import Crop
from app.models.procurement_centre import ProcurementCentre


def _clean_phone_number(mobile: str) -> str:
    """Normalize phone number to 10-digit Indian mobile format."""
    clean = mobile.lstrip("+").replace("91", "", 1).lstrip("0")
    if len(clean) > 10:
        clean = clean[-10:]
    return clean


async def lookup_farmer_by_mobile(mobile: str, db: Optional[AsyncSession] = None) -> User | None:
    """
    Find a farmer by their 10-digit mobile (strips +91 prefix and country code).
    Can be called with an active db session or will open a standalone session.
    """
    clean = _clean_phone_number(mobile)
    
    async def _query(session: AsyncSession):
        result = await session.execute(
            select(User).where(User.mobile == clean, User.role == UserRole.FARMER)
        )
        return result.scalar_one_or_none()

    if db is not None:
        return await _query(db)
    
    async with AsyncSessionLocal() as session:
        return await _query(session)


async def get_active_booking(farmer_id: uuid.UUID, db: Optional[AsyncSession] = None) -> dict | None:
    """
    Return the farmer's most relevant booking + queue position. None if none.

    Uses the shared priority selector (#19) so an in-queue or processing
    booking is never hidden behind a freshly booked future slot, and a fully
    paid cycle is treated as "no active booking".
    """
    from app.services.booking_selection import select_relevant_booking

    async def _query(session: AsyncSession):
        booking = await select_relevant_booking(session, farmer_id)
        if not booking:
            return None

        crop_result = await session.execute(select(Crop).where(Crop.id == booking.crop_id))
        crop = crop_result.scalar_one_or_none()

        centre_result = await session.execute(
            select(ProcurementCentre).where(ProcurementCentre.id == booking.centre_id)
        )
        centre = centre_result.scalar_one_or_none()

        queue_result = await session.execute(
            select(QueueEntry).where(QueueEntry.slot_booking_id == booking.id)
        )
        entry = queue_result.scalar_one_or_none()

        return {
            "token": booking.token_number,
            "status": booking.status.value,
            "crop": crop.name if crop else "your crop",
            "centre": centre.name if centre else "the mandi",
            "slot_date": booking.slot_date.strftime("%d %B"),
            "slot_time": booking.slot_start_time.strftime("%I:%M %p") if booking.slot_start_time else "",
            "queue_position": entry.position if entry else None,
            "eta_minutes": entry.estimated_wait_minutes if entry else None,
        }

    if db is not None:
        return await _query(db)

    async with AsyncSessionLocal() as session:
        return await _query(session)


# Backward compatibility alias
get_farmer_queue_status = get_active_booking


async def create_ivr_grievance(
    farmer_id: uuid.UUID,
    category: GrievanceCategory,
    db: Optional[AsyncSession] = None,
) -> str:
    """
    Create a grievance record from an IVR call. Returns short reference ID (e.g. GRV-XXXX).
    """
    async def _create(session: AsyncSession):
        result = await session.execute(
            select(SlotBooking)
            .where(SlotBooking.farmer_id == farmer_id)
            .order_by(SlotBooking.created_at.desc())
            .limit(1)
        )
        booking = result.scalar_one_or_none()

        grv = Grievance(
            id=uuid.uuid4(),
            farmer_id=farmer_id,
            slot_booking_id=booking.id if booking else None,
            category=category,
            description=f"Grievance registered via IVR Voice Helpline. Category: {category.value}",
            status=GrievanceStatus.OPEN,
        )
        session.add(grv)
        await session.commit()
        return f"GRV-{str(grv.id)[:8].upper()}"

    if db is not None:
        return await _create(db)

    async with AsyncSessionLocal() as session:
        return await _create(session)