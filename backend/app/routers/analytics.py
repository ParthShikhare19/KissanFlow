"""Analytics and mock integrations routers."""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.procurement_centre import ProcurementCentre
from app.models.slot_booking import SlotBooking, BookingStatus
from app.models.alert_log import AlertLog, AlertType
from app.schemas.dashboard import CongestionPrediction
from app.schemas.common import APIResponse
from app.middleware.auth import CurrentUser
from app.services.mock_pfms import MockAadhaarService, MockPFMSService, MockSMSService
from app.models.notification import Notification, NotificationChannel
import uuid as uuid_module

analytics_router = APIRouter(tags=["analytics"])
mock_router = APIRouter(tags=["mock-integrations"])

_aadhaar_svc = MockAadhaarService()
_pfms_svc = MockPFMSService()
_sms_svc = MockSMSService()


@analytics_router.get("/congestion-prediction/{centre_id}", response_model=APIResponse[CongestionPrediction])
async def predict_congestion(
    centre_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    centre_result = await db.execute(
        select(ProcurementCentre).where(ProcurementCentre.id == centre_id)
    )
    centre = centre_result.scalar_one_or_none()
    if not centre:
        raise HTTPException(status_code=404, detail="Centre not found")

    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).date()
    count_result = await db.execute(
        select(func.count()).where(
            SlotBooking.centre_id == centre_id,
            SlotBooking.slot_date == tomorrow,
            SlotBooking.status != BookingStatus.CANCELLED,
        )
    )
    predicted = count_result.scalar() or 0
    pct = round(predicted / centre.daily_capacity * 100, 1) if centre.daily_capacity > 0 else 0

    if pct >= 95:
        risk = "critical"
    elif pct >= 85:
        risk = "high"
    elif pct >= 65:
        risk = "moderate"
    else:
        risk = "low"

    return APIResponse(success=True, data=CongestionPrediction(
        centre_id=centre_id,
        date=tomorrow.isoformat(),
        predicted_bookings=predicted,
        daily_capacity=centre.daily_capacity,
        predicted_occupancy_pct=pct,
        risk_level=risk,
    ))


@analytics_router.get("/anomaly-flags", response_model=APIResponse[list[dict]])
async def get_anomaly_flags(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    result = await db.execute(
        select(AlertLog).where(
            AlertLog.type == AlertType.ANOMALY,
            AlertLog.is_acknowledged == False,
        ).order_by(AlertLog.created_at.desc()).limit(20)
    )
    alerts = result.scalars().all()
    return APIResponse(success=True, data=[
        {
            "id": str(a.id),
            "centre_id": str(a.centre_id),
            "message": a.message,
            "severity": a.severity.value,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ])


# ─── Mock Integrations ────────────────────────────────────────────────────────

@mock_router.post("/aadhaar/verify", response_model=APIResponse[dict])
async def verify_aadhaar(body: dict):
    """Mock Aadhaar verification — accepts any 12-digit number."""
    aadhaar = body.get("aadhaar_number", "")
    result = await _aadhaar_svc.verify(aadhaar)
    return APIResponse(success=result["verified"], data=result)


@mock_router.post("/pfms/initiate", response_model=APIResponse[dict])
async def pfms_initiate(body: dict):
    """Mock PFMS payment initiation — 2 second simulated delay."""
    farmer_id = body.get("farmer_id", str(uuid_module.uuid4()))
    amount = body.get("amount", 0)
    result = await _pfms_svc.initiate_payment(
        farmer_id=uuid_module.UUID(farmer_id) if farmer_id else uuid_module.uuid4(),
        amount=amount,
        bank_account=body.get("bank_account"),
        bank_ifsc=body.get("bank_ifsc"),
    )
    return APIResponse(success=True, data=result)


@mock_router.put("/pfms/confirm/{pfms_ref}", response_model=APIResponse[dict])
async def pfms_confirm(pfms_ref: str):
    """Mock PFMS payment confirmation — 3 second simulated delay."""
    result = await _pfms_svc.confirm_payment(pfms_ref)
    return APIResponse(success=True, data=result)


@mock_router.post("/sms/send", response_model=APIResponse[dict])
async def send_sms(
    body: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Mock SMS send — logs to console and stores Notification."""
    mobile = body.get("mobile", "")
    message = body.get("message", "")
    user_id = body.get("user_id")

    result = await _sms_svc.send(mobile, message)

    if user_id:
        notif = Notification(
            id=uuid_module.uuid4(),
            user_id=uuid_module.UUID(user_id),
            title="SMS Sent",
            body=message,
            channel=NotificationChannel.SMS,
        )
        db.add(notif)
        await db.commit()

    return APIResponse(success=True, data=result)
