"""Slot Bookings router."""
import uuid
import json
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.slot_booking import SlotBooking, BookingStatus
from app.models.user import User, UserRole
from app.schemas.booking import BookingCreate, BookingResponse, BookingWithQR
from app.schemas.common import APIResponse
from app.middleware.auth import CurrentUser, require_role
from app.services.slot_allocation import SlotAllocationService
from app.utils.qr_generator import generate_qr_base64

router = APIRouter(tags=["bookings"])
allocation_service = SlotAllocationService()


def _booking_with_details_query():
    return select(SlotBooking).options(
        selectinload(SlotBooking.farmer),
        selectinload(SlotBooking.centre),
        selectinload(SlotBooking.crop),
    )


def _booking_response(booking: SlotBooking) -> BookingResponse:
    """Return booking details with a freshly generated QR image."""
    response = BookingResponse.model_validate(booking)
    response.qr_code_base64 = generate_qr_base64(json.loads(booking.qr_code_data))
    return response


@router.post("/", response_model=APIResponse[BookingWithQR], status_code=201)
async def create_booking(
    body: BookingCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    """Create a slot booking using the smart allocation engine."""
    try:
        booking = await allocation_service.allocate(
            farmer_id=current_user.id,
            centre_id=body.centre_id,
            crop_id=body.crop_id,
            preferred_date=body.preferred_date,
            declared_qty=body.declared_quantity_q,
            preferred_slot_start_time=body.preferred_slot_start_time,
            db=db,
        )
        await db.commit()
        await db.refresh(booking, attribute_names=["farmer", "centre", "crop"])

        # Extract QR base64 from the temporarily stored JSON
        qr_data = json.loads(booking.qr_code_data)
        qr_base64 = qr_data.pop("_qr_base64", None)
        # Store clean JSON back
        booking.qr_code_data = json.dumps(qr_data)
        await db.commit()

        response = BookingWithQR.model_validate(booking)
        response.qr_code_base64 = qr_base64
        return APIResponse(success=True, data=response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{booking_id}", response_model=APIResponse[BookingResponse])
async def get_booking(
    booking_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    result = await db.execute(_booking_with_details_query().where(SlotBooking.id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.farmer_id != current_user.id and current_user.role not in [
        UserRole.MANDI_STAFF, UserRole.MANDI_OFFICER, UserRole.GOVT_ADMIN
    ]:
        raise HTTPException(status_code=403, detail="Not authorized to view this booking")
    return APIResponse(success=True, data=_booking_response(booking))


@router.get("/token/{token_number}", response_model=APIResponse[BookingResponse])
async def get_booking_by_token(
    token_number: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.MANDI_STAFF, UserRole.MANDI_OFFICER]))],
):
    """Look up a booking from the human-readable token used at the gate."""
    result = await db.execute(
        _booking_with_details_query().where(SlotBooking.token_number == token_number.upper())
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.farmer_id != current_user.id and current_user.role not in [
        UserRole.MANDI_STAFF, UserRole.MANDI_OFFICER, UserRole.GOVT_ADMIN
    ]:
        raise HTTPException(status_code=403, detail="Not authorized to view this booking")
    return APIResponse(success=True, data=_booking_response(booking))


@router.put("/{booking_id}/cancel", response_model=APIResponse[BookingResponse])
async def cancel_booking(
    booking_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    result = await db.execute(select(SlotBooking).where(SlotBooking.id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.farmer_id != current_user.id and current_user.role not in [
        UserRole.MANDI_STAFF, UserRole.MANDI_OFFICER, UserRole.GOVT_ADMIN
    ]:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this booking")

    if booking.status in [BookingStatus.COMPLETED, BookingStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel booking with status {booking.status.value}")

    booking.status = BookingStatus.CANCELLED
    await db.commit()
    await db.refresh(booking)
    return APIResponse(success=True, data=_booking_response(booking))


@router.get("/{booking_id}/qr", response_model=APIResponse[dict])
async def get_booking_qr(
    booking_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    """Return the QR code as a fresh base64 PNG."""
    result = await db.execute(select(SlotBooking).where(SlotBooking.id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.farmer_id != current_user.id and current_user.role not in [
        UserRole.MANDI_STAFF, UserRole.MANDI_OFFICER, UserRole.GOVT_ADMIN
    ]:
        raise HTTPException(status_code=403, detail="Not authorized to view this booking")

    qr_data = json.loads(booking.qr_code_data)
    qr_base64 = generate_qr_base64(qr_data)
    return APIResponse(success=True, data={"qr_code_base64": qr_base64, "token_number": booking.token_number})
