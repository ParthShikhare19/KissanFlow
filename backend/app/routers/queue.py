"""Queue management router: gate entry, queue list, positions, call-next."""
import uuid
from datetime import date, datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.slot_booking import SlotBooking, BookingStatus
from app.models.queue_entry import QueueEntry, QueueStatus
from app.models.procurement_centre import ProcurementCentre
from app.models.transaction import Transaction, PaymentStatus
from app.models.user import User, UserRole
from app.schemas.queue import GateEntryRequest, QueueEntryResponse, QueuePositionResponse, CallNextRequest
from app.schemas.common import APIResponse
from app.middleware.auth import CurrentUser, require_role
from app.socketio_server import emit_queue_updated, emit_your_turn, emit_queue_position

router = APIRouter(tags=["queue"])

# Roles allowed to operate the gate / queue at a centre.
QUEUE_OPERATOR_ROLES = [UserRole.MANDI_STAFF, UserRole.MANDI_OFFICER]


async def _enforce_centre_assignment(
    current_user: User,
    centre_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """Staff may only operate the centre they are assigned to (#10).

    Officers may also act as backup operators at any centre, but staff are
    hard-bound to their assignment.
    """
    if current_user.role != UserRole.MANDI_STAFF:
        return
    if current_user.assigned_centre_id != centre_id:
        raise HTTPException(
            status_code=403,
            detail="You are not assigned to this centre's queue",
        )


def _booking_admission_error(booking: SlotBooking, today: date) -> str | None:
    """Return a rejection reason if the booking cannot be admitted at the gate (#4)."""
    if booking.status == BookingStatus.CANCELLED:
        return "Booking is cancelled"
    if booking.status in [BookingStatus.ARRIVED, BookingStatus.IN_QUEUE, BookingStatus.PROCESSING]:
        return None  # already inside — caller handles the idempotent path
    if booking.status == BookingStatus.COMPLETED:
        return "Booking is already completed"
    if booking.status == BookingStatus.NO_SHOW:
        return "Booking was marked as a no-show"
    if booking.status == BookingStatus.PROCESSING:
        return None
    # BOOKED: only today's bookings may enter the gate.
    if booking.slot_date > today:
        return "Booking is for a future date — admit at the gate on the slot date"
    if booking.slot_date < today:
        return "Booking date has passed — ask the farmer to rebook"
    return None


async def _build_queue_payload(db: AsyncSession, centre_id: uuid.UUID) -> list[dict]:
    """Build full queue list payload for Socket.IO emit."""
    result = await db.execute(
        select(QueueEntry)
        .where(
            QueueEntry.centre_id == centre_id,
            QueueEntry.status.in_([QueueStatus.WAITING, QueueStatus.CALLED, QueueStatus.PROCESSING])
        )
        .order_by(QueueEntry.position)
    )
    entries = result.scalars().all()
    payload = []
    for e in entries:
        booking_result = await db.execute(
            select(SlotBooking).where(SlotBooking.id == e.slot_booking_id)
        )
        booking = booking_result.scalar_one_or_none()
        farmer_name = None
        crop_name = None
        if booking:
            farmer_result = await db.execute(select(User).where(User.id == booking.farmer_id))
            farmer = farmer_result.scalar_one_or_none()
            farmer_name = farmer.name if farmer else None
            from app.models.crop import Crop
            crop_result = await db.execute(select(Crop).where(Crop.id == booking.crop_id))
            crop = crop_result.scalar_one_or_none()
            crop_name = crop.name if crop else None

        payload.append({
            "id": str(e.id),
            "slot_booking_id": str(e.slot_booking_id),
            "position": e.position,
            "estimated_wait_minutes": e.estimated_wait_minutes,
            "status": e.status.value,
            "farmer_name": farmer_name,
            "token_number": booking.token_number if booking else None,
            "crop_name": crop_name,
            "declared_quantity_q": booking.declared_quantity_q if booking else None,
        })
    return payload


async def _emit_farmer_positions(db: AsyncSession, centre_id: uuid.UUID) -> None:
    """Push each waiting farmer's live position to their personal socket room (#7)."""
    result = await db.execute(
        select(QueueEntry).where(
            QueueEntry.centre_id == centre_id,
            QueueEntry.status.in_([QueueStatus.WAITING, QueueStatus.CALLED, QueueStatus.PROCESSING]),
        )
    )
    entries = result.scalars().all()
    for e in entries:
        ahead_result = await db.execute(
            select(func.count()).where(
                QueueEntry.centre_id == centre_id,
                QueueEntry.status == QueueStatus.WAITING,
                QueueEntry.position < e.position,
            )
        )
        ahead = ahead_result.scalar() or 0
        await emit_queue_position(str(e.slot_booking_id), {
            "position": e.position,
            "estimated_wait_minutes": e.estimated_wait_minutes,
            "status": e.status.value,
            "ahead_of_you": ahead,
        })


@router.post("/gate-entry", response_model=APIResponse[QueueEntryResponse])
async def gate_entry(
    body: GateEntryRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(QUEUE_OPERATOR_ROLES))],
):
    """Mark farmer as arrived and add to queue."""
    # Find booking by token or ID
    if body.token_number:
        result = await db.execute(
            select(SlotBooking).where(SlotBooking.token_number == body.token_number)
        )
    elif body.booking_id:
        result = await db.execute(
            select(SlotBooking).where(SlotBooking.id == body.booking_id)
        )
    else:
        raise HTTPException(status_code=400, detail="Provide token_number or booking_id")

    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    await _enforce_centre_assignment(current_user, booking.centre_id, db)

    today = datetime.now(timezone.utc).date()
    rejection = _booking_admission_error(booking, today)
    if rejection:
        raise HTTPException(status_code=400, detail=rejection)

    if booking.status in [BookingStatus.ARRIVED, BookingStatus.IN_QUEUE, BookingStatus.PROCESSING]:
        # Already in queue — return existing entry
        existing_result = await db.execute(
            select(QueueEntry).where(QueueEntry.slot_booking_id == booking.id)
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            return APIResponse(success=True, data=QueueEntryResponse.model_validate(existing))

    # Block paid/completed procurement double-entry via a linked transaction
    txn_result = await db.execute(
        select(Transaction).where(
            Transaction.slot_booking_id == booking.id,
            Transaction.payment_status == PaymentStatus.PAID,
        )
    )
    if txn_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Procurement for this booking is already paid")

    # Mark booking as ARRIVED
    booking.status = BookingStatus.ARRIVED

    # Get current queue size to assign position
    centre_result = await db.execute(
        select(ProcurementCentre).where(ProcurementCentre.id == booking.centre_id)
    )
    centre = centre_result.scalar_one()

    count_result = await db.execute(
        select(func.count()).where(
            QueueEntry.centre_id == booking.centre_id,
            QueueEntry.status.in_([QueueStatus.WAITING, QueueStatus.CALLED, QueueStatus.PROCESSING])
        )
    )
    queue_size = count_result.scalar() or 0
    position = queue_size + 1
    eta = position * centre.avg_processing_time_minutes

    entry = QueueEntry(
        id=uuid.uuid4(),
        slot_booking_id=booking.id,
        centre_id=booking.centre_id,
        position=position,
        estimated_wait_minutes=eta,
        status=QueueStatus.WAITING,
        gate_entry_time=datetime.now(timezone.utc),
    )
    booking.status = BookingStatus.IN_QUEUE
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    # Emit real-time queue update
    queue_payload = await _build_queue_payload(db, booking.centre_id)
    await emit_queue_updated(str(booking.centre_id), queue_payload)
    await _emit_farmer_positions(db, booking.centre_id)

    return APIResponse(success=True, data=QueueEntryResponse.model_validate(entry))


@router.get("/{centre_id}", response_model=APIResponse[list[QueueEntryResponse]])
async def get_queue(
    centre_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    """Get full queue for a centre."""
    await _enforce_centre_assignment(current_user, centre_id, db)
    result = await db.execute(
        select(QueueEntry)
        .where(
            QueueEntry.centre_id == centre_id,
            QueueEntry.status.in_([QueueStatus.WAITING, QueueStatus.CALLED, QueueStatus.PROCESSING])
        )
        .order_by(QueueEntry.position)
    )
    entries = result.scalars().all()

    enriched = []
    for e in entries:
        entry_resp = QueueEntryResponse.model_validate(e)
        booking_result = await db.execute(
            select(SlotBooking).where(SlotBooking.id == e.slot_booking_id)
        )
        booking = booking_result.scalar_one_or_none()
        if booking:
            farmer_result = await db.execute(select(User).where(User.id == booking.farmer_id))
            farmer = farmer_result.scalar_one_or_none()
            entry_resp.farmer_name = farmer.name if farmer else None
            entry_resp.token_number = booking.token_number
            entry_resp.declared_quantity_q = booking.declared_quantity_q
            from app.models.crop import Crop
            crop_result = await db.execute(select(Crop).where(Crop.id == booking.crop_id))
            crop = crop_result.scalar_one_or_none()
            entry_resp.crop_name = crop.name if crop else None
        enriched.append(entry_resp)

    return APIResponse(success=True, data=enriched)


@router.get("/position/{booking_id}", response_model=APIResponse[QueuePositionResponse])
async def get_queue_position(
    booking_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    result = await db.execute(
        select(QueueEntry).where(QueueEntry.slot_booking_id == booking_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Not in queue")

    # Ownership: the farmer may read their own position; privileged roles and
    # staff may read any.
    if current_user.role not in [
        UserRole.MANDI_STAFF, UserRole.MANDI_OFFICER, UserRole.GOVT_ADMIN, UserRole.CSC_OPERATOR
    ]:
        booking_result = await db.execute(
            select(SlotBooking).where(SlotBooking.id == booking_id)
        )
        booking = booking_result.scalar_one_or_none()
        if not booking or booking.farmer_id != current_user.id:
            raise HTTPException(status_code=403, detail="Cannot view another farmer's queue position")

    ahead_result = await db.execute(
        select(func.count()).where(
            QueueEntry.centre_id == entry.centre_id,
            QueueEntry.status == QueueStatus.WAITING,
            QueueEntry.position < entry.position,
        )
    )
    ahead = ahead_result.scalar() or 0

    return APIResponse(success=True, data=QueuePositionResponse(
        booking_id=booking_id,
        position=entry.position,
        estimated_wait_minutes=entry.estimated_wait_minutes,
        status=entry.status,
        ahead_of_you=ahead,
    ))


@router.post("/call-next", response_model=APIResponse[QueueEntryResponse | None])
async def call_next(
    body: CallNextRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(QUEUE_OPERATOR_ROLES))],
):
    """Mark current CALLED/PROCESSING entry as DONE, call next WAITING entry."""
    await _enforce_centre_assignment(current_user, body.centre_id, db)

    # Complete any currently processing entry
    processing_result = await db.execute(
        select(QueueEntry).where(
            QueueEntry.centre_id == body.centre_id,
            QueueEntry.status.in_([QueueStatus.CALLED, QueueStatus.PROCESSING])
        ).limit(1)
    )
    current = processing_result.scalar_one_or_none()
    if current:
        current.status = QueueStatus.DONE
        booking_result = await db.execute(
            select(SlotBooking).where(SlotBooking.id == current.slot_booking_id)
        )
        done_booking = booking_result.scalar_one_or_none()
        if done_booking:
            done_booking.status = BookingStatus.PROCESSING

    # Call next WAITING entry
    next_result = await db.execute(
        select(QueueEntry).where(
            QueueEntry.centre_id == body.centre_id,
            QueueEntry.status == QueueStatus.WAITING,
        ).order_by(QueueEntry.position).limit(1)
    )
    next_entry = next_result.scalar_one_or_none()
    if next_entry:
        next_entry.status = QueueStatus.CALLED
        booking_result = await db.execute(
            select(SlotBooking).where(SlotBooking.id == next_entry.slot_booking_id)
        )
        next_booking = booking_result.scalar_one_or_none()
        if next_booking:
            next_booking.status = BookingStatus.PROCESSING
            # Notify farmer
            await emit_your_turn(str(next_booking.id))

    await db.commit()

    # Emit updated queue
    queue_payload = await _build_queue_payload(db, body.centre_id)
    await emit_queue_updated(str(body.centre_id), queue_payload)
    await _emit_farmer_positions(db, body.centre_id)

    if next_entry:
        await db.refresh(next_entry)
        return APIResponse(success=True, data=QueueEntryResponse.model_validate(next_entry))
    return APIResponse(success=True, data=None)


@router.post("/complete/{booking_id}", response_model=APIResponse[dict])
async def complete_queue_entry(
    booking_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(QUEUE_OPERATOR_ROLES))],
):
    result = await db.execute(
        select(QueueEntry).where(QueueEntry.slot_booking_id == booking_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")

    await _enforce_centre_assignment(current_user, entry.centre_id, db)

    entry.status = QueueStatus.DONE
    booking_result = await db.execute(select(SlotBooking).where(SlotBooking.id == booking_id))
    booking = booking_result.scalar_one_or_none()
    if booking:
        booking.status = BookingStatus.COMPLETED

    await db.commit()

    queue_payload = await _build_queue_payload(db, entry.centre_id)
    await emit_queue_updated(str(entry.centre_id), queue_payload)
    await _emit_farmer_positions(db, entry.centre_id)

    return APIResponse(success=True, data={"message": "Queue entry marked as done"})
