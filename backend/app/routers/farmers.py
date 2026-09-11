"""Farmers router: profile, timeline, transactions, grievances, notifications."""
import uuid
import json
from typing import Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import CurrentUser, require_role
from app.models.user import User, UserRole
from app.models.farmer_profile import FarmerProfile
from app.models.slot_booking import SlotBooking, BookingStatus
from app.models.queue_entry import QueueEntry, QueueStatus
from app.models.transaction import Transaction
from app.models.grievance import Grievance
from app.models.notification import Notification
from app.schemas.user import FarmerProfileResponse, FarmerProfileUpdate, TimelineEvent, FarmerWithProfileResponse
from app.schemas.booking import BookingResponse
from app.schemas.transaction import TransactionResponse
from app.schemas.grievance import GrievanceResponse
from app.schemas.notification import NotificationResponse
from app.schemas.common import APIResponse, PaginatedResponse, paginated_response
from app.services.booking_selection import select_relevant_booking
from app.utils.qr_generator import generate_qr_base64

router = APIRouter(tags=["farmers"])

# Roles that may view another farmer's records (assistants and oversight).
FARMER_VIEWER_ROLES = [UserRole.MANDI_STAFF, UserRole.MANDI_OFFICER, UserRole.GOVT_ADMIN, UserRole.CSC_OPERATOR]


def _enforce_farmer_access(current_user: User, farmer_id: uuid.UUID, action: str = "view") -> None:
    """Farmers may only access their own records (#2)."""
    if current_user.id != farmer_id and current_user.role not in FARMER_VIEWER_ROLES:
        raise HTTPException(status_code=403, detail=f"Cannot {action} another farmer's data")


def _duration_minutes(start: datetime | None, end: datetime | None) -> int | None:
    if not start or not end:
        return None
    return max(0, round((end - start).total_seconds() / 60))


@router.get("/{farmer_id}/bookings/latest", response_model=APIResponse[BookingResponse | None])
async def get_latest_booking(
    farmer_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    """Return the farmer's most relevant booking for dashboard queue updates.

    Uses priority selection (#5/#19): in-queue/processing first, then upcoming
    booked slot, then unpaid completed — never lets a future booking hide an
    active queue position, and a fully paid cycle returns None so the
    dashboard resets (#13).
    """
    _enforce_farmer_access(current_user, farmer_id, "view")

    booking = await select_relevant_booking(db, farmer_id)
    booking_response = None
    if booking:
        booking = await db.scalar(
            select(SlotBooking)
            .options(
                selectinload(SlotBooking.farmer),
                selectinload(SlotBooking.centre),
                selectinload(SlotBooking.crop),
            )
            .where(SlotBooking.id == booking.id)
        )
        booking_response = BookingResponse.model_validate(booking)
        booking_response.qr_code_base64 = generate_qr_base64(json.loads(booking.qr_code_data))
    return APIResponse(success=True, data=booking_response)


@router.get("/{farmer_id}/process-summary", response_model=APIResponse[list[dict]])
async def get_farmer_process_summary(
    farmer_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    """Return real elapsed times for the farmer's recent procurement cycles.

    Uses persisted per-stage timestamps (#18): quality_done_at,
    weighment_done_at, confirmed_at, payment_initiated_at, paid_at — with a
    fallback to legacy timestamps for rows created before those columns.
    """
    _enforce_farmer_access(current_user, farmer_id, "view")

    result = await db.execute(
        select(SlotBooking)
        .where(SlotBooking.farmer_id == farmer_id)
        .order_by(SlotBooking.created_at.desc())
        .limit(50)
    )
    bookings = result.scalars().all()
    summary = []
    for booking in bookings:
        queue_result = await db.execute(
            select(QueueEntry).where(QueueEntry.slot_booking_id == booking.id)
        )
        queue_entry = queue_result.scalar_one_or_none()
        txn_result = await db.execute(
            select(Transaction).where(Transaction.slot_booking_id == booking.id)
        )
        transaction = txn_result.scalar_one_or_none()
        gate_entry = queue_entry.gate_entry_time if queue_entry else None
        processing_started = transaction.created_at if transaction else None
        completed_at = (
            transaction.paid_at or transaction.completed_at
        ) if transaction else None
        quality_done = transaction.quality_done_at if transaction else None
        weighment_done = transaction.weighment_done_at if transaction else None
        confirmed = transaction.confirmed_at if transaction else None
        payment_initiated = transaction.payment_initiated_at if transaction else None
        summary.append({
            "booking_id": str(booking.id),
            "token_number": booking.token_number,
            "status": booking.status.value,
            "slot_date": booking.slot_date.isoformat(),
            "booking_to_gate_minutes": _duration_minutes(booking.created_at, gate_entry),
            "gate_to_processing_minutes": _duration_minutes(gate_entry, processing_started),
            "quality_check_minutes": _duration_minutes(processing_started, quality_done),
            "weighment_minutes": _duration_minutes(quality_done, weighment_done),
            "confirmation_minutes": _duration_minutes(weighment_done, confirmed),
            "payment_minutes": _duration_minutes(payment_initiated, completed_at),
            "processing_to_completion_minutes": _duration_minutes(processing_started, completed_at),
            "total_cycle_minutes": _duration_minutes(booking.created_at, completed_at),
            "payment_status": transaction.payment_status.value if transaction else None,
        })
    summary.sort(
        key=lambda item: (
            item["total_cycle_minutes"] is None,
            item["status"] not in ["PROCESSING", "IN_QUEUE"],
            item["slot_date"],
        )
    )
    return APIResponse(success=True, data=summary)


@router.get("/{farmer_id}/profile", response_model=APIResponse[FarmerWithProfileResponse])
async def get_farmer_profile(
    farmer_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    _enforce_farmer_access(current_user, farmer_id, "view")
    result = await db.execute(
        select(User)
        .options(selectinload(User.farmer_profile))
        .where(User.id == farmer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Farmer not found")

    response = FarmerWithProfileResponse.model_validate(user)
    return APIResponse(success=True, data=response)


@router.put("/{farmer_id}/profile", response_model=APIResponse[FarmerProfileResponse])
async def update_farmer_profile(
    farmer_id: uuid.UUID,
    body: FarmerProfileUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    _enforce_farmer_access(current_user, farmer_id, "update")

    result = await db.execute(
        select(FarmerProfile).where(FarmerProfile.user_id == farmer_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Farmer profile not found")

    for field, value in body.model_dump(exclude_none=True).items():
        if field == "bank_account_number":
            setattr(profile, "bank_account_number_encrypted", value)
        else:
            setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return APIResponse(success=True, data=FarmerProfileResponse.model_validate(profile))


@router.get("/{farmer_id}/timeline", response_model=APIResponse[list[TimelineEvent]])
async def get_farmer_timeline(
    farmer_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    booking_id: uuid.UUID | None = Query(None),
):
    """Build a procurement status timeline for the farmer's relevant booking."""
    _enforce_farmer_access(current_user, farmer_id, "view")

    if booking_id:
        result = await db.execute(
            select(SlotBooking).where(
                SlotBooking.id == booking_id, SlotBooking.farmer_id == farmer_id
            )
        )
        booking = result.scalar_one_or_none()
    else:
        booking = await select_relevant_booking(db, farmer_id)

    if not booking:
        return APIResponse(success=True, data=[])

    txn_result = await db.execute(
        select(Transaction).where(Transaction.slot_booking_id == booking.id)
    )
    txn = txn_result.scalar_one_or_none()

    def stage(name: str, label: str, condition: bool, timestamp=None, detail=None) -> TimelineEvent:
        return TimelineEvent(
            stage=name,
            label=label,
            status="completed" if condition else "pending",
            timestamp=timestamp,
            detail=detail,
        )

    timeline = [
        TimelineEvent(stage="registered", label="Farmer Registered", status="completed", timestamp=booking.created_at),
        stage("slot_booked", "Slot Booked", True, booking.created_at, f"Token: {booking.token_number}"),
        stage("arrived", "Arrived at Mandi", booking.status in [
            BookingStatus.ARRIVED, BookingStatus.IN_QUEUE,
            BookingStatus.PROCESSING, BookingStatus.COMPLETED
        ]),
        stage("in_queue", "In Queue", booking.status in [
            BookingStatus.IN_QUEUE, BookingStatus.PROCESSING, BookingStatus.COMPLETED
        ]),
        stage("processing", "Processing Started", booking.status in [
            BookingStatus.PROCESSING, BookingStatus.COMPLETED
        ]),
        stage("quality_check", "Quality Check Done",
              txn is not None and txn.quality_status is not None,
              timestamp=txn.quality_done_at if txn else None,
              detail=txn.quality_status.value if txn and txn.quality_status else None),
        stage("weighment", "Weighment Done",
              txn is not None and txn.net_weight_q is not None,
              timestamp=txn.weighment_done_at if txn else None,
              detail=f"{txn.net_weight_q}Q" if txn and txn.net_weight_q else None),
        stage("procurement_confirmed", "Procurement Confirmed",
              txn is not None and txn.procurement_status.value == "CONFIRMED",
              timestamp=txn.confirmed_at if txn else None,
              detail=f"₹{txn.total_amount:,.0f}" if txn and txn.total_amount else None),
        stage("payment_initiated", "Payment Initiated",
              txn is not None and txn.payment_status.value in ["INITIATED", "PROCESSING", "PAID"],
              timestamp=txn.payment_initiated_at if txn else None),
        stage("payment_done", "Payment Completed",
              txn is not None and txn.payment_status.value == "PAID",
              timestamp=txn.paid_at if txn else None,
              detail=f"Ref: {txn.payment_ref}" if txn and txn.payment_ref else None),
    ]
    return APIResponse(success=True, data=timeline)


@router.get("/{farmer_id}/transactions", response_model=APIResponse[PaginatedResponse[TransactionResponse]])
async def get_farmer_transactions(
    farmer_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    _enforce_farmer_access(current_user, farmer_id, "view")
    offset = (page - 1) * page_size
    count_result = await db.execute(
        select(func.count()).where(Transaction.farmer_id == farmer_id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Transaction).where(Transaction.farmer_id == farmer_id)
        .order_by(Transaction.created_at.desc())
        .offset(offset).limit(page_size)
    )
    txns = result.scalars().all()
    items = [TransactionResponse.model_validate(t) for t in txns]
    return APIResponse(success=True, data=paginated_response(items, total, page, page_size))


@router.get("/{farmer_id}/grievances", response_model=APIResponse[PaginatedResponse[GrievanceResponse]])
async def get_farmer_grievances(
    farmer_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    _enforce_farmer_access(current_user, farmer_id, "view")
    offset = (page - 1) * page_size
    count_result = await db.execute(
        select(func.count()).where(Grievance.farmer_id == farmer_id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Grievance).where(Grievance.farmer_id == farmer_id)
        .order_by(Grievance.created_at.desc())
        .offset(offset).limit(page_size)
    )
    grievances = result.scalars().all()
    items = [GrievanceResponse.model_validate(g) for g in grievances]
    return APIResponse(success=True, data=paginated_response(items, total, page, page_size))


@router.get("/{farmer_id}/notifications", response_model=APIResponse[PaginatedResponse[NotificationResponse]])
async def get_farmer_notifications(
    farmer_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    _enforce_farmer_access(current_user, farmer_id, "view")
    offset = (page - 1) * page_size
    count_result = await db.execute(
        select(func.count()).where(Notification.user_id == farmer_id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Notification).where(Notification.user_id == farmer_id)
        .order_by(Notification.created_at.desc())
        .offset(offset).limit(page_size)
    )
    notifications = result.scalars().all()
    items = [NotificationResponse.model_validate(n) for n in notifications]
    return APIResponse(success=True, data=paginated_response(items, total, page, page_size))
