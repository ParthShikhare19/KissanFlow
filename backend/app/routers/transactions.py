"""Transactions router: create, quality check, weighment, confirm, payment."""
import uuid
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.slot_booking import SlotBooking, BookingStatus
from app.models.transaction import Transaction, PaymentStatus, ProcurementStatus
from app.models.user import User, UserRole
from app.models.farmer_profile import FarmerProfile
from app.models.notification import Notification, NotificationChannel
from app.schemas.transaction import TransactionCreate, QualityUpdate, WeighmentUpdate, TransactionResponse
from app.schemas.common import APIResponse
from app.middleware.auth import CurrentUser, require_role
from app.services.mock_pfms import MockPFMSService

router = APIRouter(tags=["transactions"])
pfms = MockPFMSService()


async def _enrich_transaction(txn: Transaction, db: AsyncSession) -> TransactionResponse:
    """Add human-readable fields to a transaction response."""
    resp = TransactionResponse.model_validate(txn)
    farmer_result = await db.execute(select(User).where(User.id == txn.farmer_id))
    farmer = farmer_result.scalar_one_or_none()
    resp.farmer_name = farmer.name if farmer else None

    from app.models.crop import Crop
    crop_result = await db.execute(select(Crop).where(Crop.id == txn.crop_id))
    crop = crop_result.scalar_one_or_none()
    resp.crop_name = crop.name if crop else None

    from app.models.procurement_centre import ProcurementCentre
    centre_result = await db.execute(
        select(ProcurementCentre).where(ProcurementCentre.id == txn.centre_id)
    )
    centre = centre_result.scalar_one_or_none()
    resp.centre_name = centre.name if centre else None
    return resp


@router.post("/", response_model=APIResponse[TransactionResponse], status_code=201)
async def create_transaction(
    body: TransactionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.MANDI_STAFF, UserRole.MANDI_OFFICER]))],
):
    """Create a transaction record linked to a slot booking."""
    booking_result = await db.execute(
        select(SlotBooking).where(SlotBooking.id == body.slot_booking_id)
    )
    booking = booking_result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Check for existing transaction
    existing_result = await db.execute(
        select(Transaction).where(Transaction.slot_booking_id == booking.id)
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        return APIResponse(success=True, data=await _enrich_transaction(existing, db))

    from app.models.crop import Crop
    crop_result = await db.execute(select(Crop).where(Crop.id == booking.crop_id))
    crop = crop_result.scalar_one_or_none()

    txn = Transaction(
        id=uuid.uuid4(),
        slot_booking_id=booking.id,
        farmer_id=booking.farmer_id,
        centre_id=booking.centre_id,
        crop_id=booking.crop_id,
        msp_per_q=crop.msp_per_quintal if crop else None,
        staff_id=current_user.id,
    )
    db.add(txn)
    booking.status = BookingStatus.PROCESSING
    await db.commit()
    await db.refresh(txn)
    return APIResponse(success=True, data=await _enrich_transaction(txn, db))


@router.get("/{transaction_id}", response_model=APIResponse[TransactionResponse])
async def get_transaction(
    transaction_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return APIResponse(success=True, data=await _enrich_transaction(txn, db))


@router.put("/{transaction_id}/quality", response_model=APIResponse[TransactionResponse])
async def update_quality(
    transaction_id: uuid.UUID,
    body: QualityUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.MANDI_STAFF, UserRole.MANDI_OFFICER]))],
):
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    txn.moisture_percent = body.moisture_percent
    txn.foreign_matter_percent = body.foreign_matter_percent
    txn.quality_status = body.quality_status
    txn.quality_notes = body.quality_notes
    txn.quality_photo_url = body.quality_photo_url

    await db.commit()
    await db.refresh(txn)
    return APIResponse(success=True, data=await _enrich_transaction(txn, db))


@router.put("/{transaction_id}/weighment", response_model=APIResponse[TransactionResponse])
async def update_weighment(
    transaction_id: uuid.UUID,
    body: WeighmentUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.MANDI_STAFF, UserRole.MANDI_OFFICER]))],
):
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    txn.gross_weight_q = body.gross_weight_q
    txn.tare_weight_q = body.tare_weight_q
    txn.net_weight_q = round(body.gross_weight_q - body.tare_weight_q, 3)
    txn.weighment_photo_url = body.weighment_photo_url

    await db.commit()
    await db.refresh(txn)
    return APIResponse(success=True, data=await _enrich_transaction(txn, db))


@router.put("/{transaction_id}/confirm", response_model=APIResponse[TransactionResponse])
async def confirm_transaction(
    transaction_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.MANDI_OFFICER, UserRole.GOVT_ADMIN]))],
):
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if txn.net_weight_q is None or txn.msp_per_q is None:
        raise HTTPException(status_code=400, detail="Weighment must be completed before confirmation")
    if txn.quality_status is None:
        raise HTTPException(status_code=400, detail="Quality check must be completed before confirmation")
    if txn.quality_status.value == "REJECTED":
        raise HTTPException(status_code=400, detail="Rejected produce cannot be confirmed for procurement")

    txn.total_amount = round(txn.net_weight_q * txn.msp_per_q, 2)
    txn.procurement_status = ProcurementStatus.CONFIRMED

    # Update booking status to COMPLETED
    booking_result = await db.execute(
        select(SlotBooking).where(SlotBooking.id == txn.slot_booking_id)
    )
    booking = booking_result.scalar_one_or_none()
    if booking:
        booking.status = BookingStatus.COMPLETED

    # Notify farmer
    notif = Notification(
        id=uuid.uuid4(),
        user_id=txn.farmer_id,
        title="Procurement Confirmed ✓",
        body=f"Your crop procurement of {txn.net_weight_q}Q has been confirmed. Total: ₹{txn.total_amount:,.0f}",
        channel=NotificationChannel.APP,
    )
    db.add(notif)
    txn.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(txn)
    return APIResponse(success=True, data=await _enrich_transaction(txn, db))


@router.put("/{transaction_id}/payment", response_model=APIResponse[TransactionResponse])
async def initiate_payment(
    transaction_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.MANDI_OFFICER, UserRole.GOVT_ADMIN]))],
):
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if txn.procurement_status != ProcurementStatus.CONFIRMED:
        raise HTTPException(status_code=400, detail="Transaction must be confirmed before payment")

    if txn.payment_status in [PaymentStatus.PAID, PaymentStatus.PROCESSING]:
        raise HTTPException(status_code=400, detail=f"Payment already in status: {txn.payment_status.value}")

    txn.payment_status = PaymentStatus.INITIATED

    # Fetch farmer bank details
    fp_result = await db.execute(
        select(FarmerProfile).where(FarmerProfile.user_id == txn.farmer_id)
    )
    fp = fp_result.scalar_one_or_none()

    # Call mock PFMS
    pfms_result = await pfms.initiate_payment(
        farmer_id=txn.farmer_id,
        amount=txn.total_amount or 0,
        bank_account=fp.bank_account_number_encrypted if fp else None,
        bank_ifsc=fp.bank_ifsc_code if fp else None,
    )
    txn.payment_ref = pfms_result["pfms_ref"]
    txn.payment_status = PaymentStatus.PROCESSING

    # Auto-confirm (simulate instant PFMS confirmation)
    confirm_result = await pfms.confirm_payment(pfms_result["pfms_ref"])
    txn.pfms_transaction_id = confirm_result["utr"]
    txn.payment_status = PaymentStatus.PAID

    # Notify farmer
    notif = Notification(
        id=uuid.uuid4(),
        user_id=txn.farmer_id,
        title="Payment Received 💰",
        body=(
            f"₹{txn.total_amount:,.0f} has been credited to your bank account. "
            f"UTR: {confirm_result['utr']}"
        ),
        channel=NotificationChannel.APP,
    )
    db.add(notif)

    await db.commit()
    await db.refresh(txn)
    return APIResponse(success=True, data=await _enrich_transaction(txn, db))
