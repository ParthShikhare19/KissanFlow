"""Farmers router: profile, timeline, transactions, grievances, notifications."""
import uuid
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
from app.models.transaction import Transaction
from app.models.grievance import Grievance
from app.models.notification import Notification
from app.schemas.user import FarmerProfileResponse, FarmerProfileUpdate, TimelineEvent, FarmerWithProfileResponse
from app.schemas.booking import BookingResponse
from app.schemas.transaction import TransactionResponse
from app.schemas.grievance import GrievanceResponse
from app.schemas.notification import NotificationResponse
from app.schemas.common import APIResponse, PaginatedResponse, paginated_response

router = APIRouter(tags=["farmers"])


@router.get("/{farmer_id}/bookings/latest", response_model=APIResponse[BookingResponse | None])
async def get_latest_booking(
    farmer_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    """Return the farmer's most recent booking for dashboard queue updates."""
    if current_user.id != farmer_id and current_user.role not in [
        UserRole.MANDI_STAFF, UserRole.MANDI_OFFICER, UserRole.GOVT_ADMIN, UserRole.CSC_OPERATOR
    ]:
        raise HTTPException(status_code=403, detail="Cannot view another farmer's booking")

    result = await db.execute(
        select(SlotBooking).options(
            selectinload(SlotBooking.farmer),
            selectinload(SlotBooking.centre),
            selectinload(SlotBooking.crop),
        )
        .where(SlotBooking.farmer_id == farmer_id)
        .order_by(SlotBooking.created_at.desc())
        .limit(1)
    )
    booking = result.scalar_one_or_none()
    return APIResponse(
        success=True,
        data=BookingResponse.model_validate(booking) if booking else None,
    )


@router.get("/{farmer_id}/profile", response_model=APIResponse[FarmerWithProfileResponse])
async def get_farmer_profile(
    farmer_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    result = await db.execute(select(User).where(User.id == farmer_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Farmer not found")

    fp_result = await db.execute(
        select(FarmerProfile).where(FarmerProfile.user_id == farmer_id)
    )
    profile = fp_result.scalar_one_or_none()
    response = FarmerWithProfileResponse.model_validate(user)
    if profile:
        response.farmer_profile = FarmerProfileResponse.model_validate(profile)
    return APIResponse(success=True, data=response)


@router.put("/{farmer_id}/profile", response_model=APIResponse[FarmerProfileResponse])
async def update_farmer_profile(
    farmer_id: uuid.UUID,
    body: FarmerProfileUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    if current_user.id != farmer_id and current_user.role not in [UserRole.MANDI_OFFICER, UserRole.GOVT_ADMIN, UserRole.CSC_OPERATOR]:
        raise HTTPException(status_code=403, detail="Cannot update another user's profile")

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
    """Build a procurement status timeline for the farmer's latest (or specified) booking."""
    query = select(SlotBooking).where(SlotBooking.farmer_id == farmer_id)
    if booking_id:
        query = query.where(SlotBooking.id == booking_id)
    else:
        query = query.order_by(SlotBooking.created_at.desc()).limit(1)

    result = await db.execute(query)
    booking = result.scalar_one_or_none()

    if not booking:
        return APIResponse(success=True, data=[])

    txn_result = await db.execute(
        select(Transaction).where(Transaction.slot_booking_id == booking.id)
    )
    txn = txn_result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

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
              detail=txn.quality_status.value if txn and txn.quality_status else None),
        stage("weighment", "Weighment Done",
              txn is not None and txn.net_weight_q is not None,
              detail=f"{txn.net_weight_q}Q" if txn and txn.net_weight_q else None),
        stage("procurement_confirmed", "Procurement Confirmed",
              txn is not None and txn.procurement_status.value == "CONFIRMED",
              detail=f"₹{txn.total_amount:,.0f}" if txn and txn.total_amount else None),
        stage("payment_initiated", "Payment Initiated",
              txn is not None and txn.payment_status.value in ["INITIATED", "PROCESSING", "PAID"]),
        stage("payment_done", "Payment Completed",
              txn is not None and txn.payment_status.value == "PAID",
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
