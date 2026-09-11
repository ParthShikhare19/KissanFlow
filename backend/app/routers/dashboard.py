"""Mandi and Government dashboard routers."""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.slot_booking import SlotBooking, BookingStatus
from app.models.transaction import Transaction, QualityStatus, PaymentStatus, ProcurementStatus
from app.models.queue_entry import QueueEntry, QueueStatus
from app.models.procurement_centre import ProcurementCentre
from app.models.alert_log import AlertLog, AlertSeverity
from app.models.grievance import Grievance, GrievanceStatus
from app.models.user import User, UserRole
from app.schemas.dashboard import MandiDashboard, GovtDashboard, DrilldownRow, AnomalyFlag
from app.schemas.alert import AlertLogResponse
from app.schemas.common import APIResponse
from app.middleware.auth import CurrentUser, require_role

mandi_router = APIRouter(tags=["mandi-dashboard"])
govt_router = APIRouter(tags=["govt-dashboard"])


# ─── Mandi Dashboard ──────────────────────────────────────────────────────────

@mandi_router.get("/{centre_id}", response_model=APIResponse[MandiDashboard])
async def get_mandi_dashboard(
    centre_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    today = datetime.now(timezone.utc).date()

    centre_result = await db.execute(
        select(ProcurementCentre).where(ProcurementCentre.id == centre_id)
    )
    centre = centre_result.scalar_one_or_none()
    if not centre:
        raise HTTPException(status_code=404, detail="Centre not found")

    # Today's bookings
    bookings_result = await db.execute(
        select(SlotBooking).where(
            SlotBooking.centre_id == centre_id,
            SlotBooking.slot_date == today,
            SlotBooking.status != BookingStatus.CANCELLED,
        )
    )
    bookings = bookings_result.scalars().all()
    total_bookings = len(bookings)
    arrived = sum(1 for b in bookings if b.status in [
        BookingStatus.ARRIVED, BookingStatus.IN_QUEUE, BookingStatus.PROCESSING, BookingStatus.COMPLETED
    ])
    completed = sum(1 for b in bookings if b.status == BookingStatus.COMPLETED)

    # Queue size
    queue_count = await db.execute(
        select(func.count()).where(
            QueueEntry.centre_id == centre_id,
            QueueEntry.status.in_([QueueStatus.WAITING, QueueStatus.CALLED, QueueStatus.PROCESSING]),
        )
    )
    queue_size = queue_count.scalar() or 0

    # Quality pending
    quality_pending = await db.execute(
        select(func.count()).where(
            Transaction.centre_id == centre_id,
            Transaction.quality_status == None,
            Transaction.procurement_status == ProcurementStatus.PENDING,
        )
    )
    quality_pending_count = quality_pending.scalar() or 0

    # Payment pending
    payment_pending = await db.execute(
        select(func.count()).where(
            Transaction.centre_id == centre_id,
            Transaction.payment_status == PaymentStatus.NOT_INITIATED,
            Transaction.procurement_status == ProcurementStatus.CONFIRMED,
        )
    )
    payment_pending_count = payment_pending.scalar() or 0

    # Active grievances
    grievances_count = await db.execute(
        select(func.count()).where(
            Grievance.status.in_([GrievanceStatus.OPEN, GrievanceStatus.UNDER_REVIEW])
        )
    )
    active_grievances = grievances_count.scalar() or 0

    # Hourly throughput today
    hourly_data = []
    for hour in range(9, 18):
        hour_start = datetime.combine(today, datetime.min.time()).replace(hour=hour, tzinfo=timezone.utc)
        hour_end = hour_start + timedelta(hours=1)
        count_result = await db.execute(
            select(func.count()).where(
                Transaction.centre_id == centre_id,
                Transaction.completed_at >= hour_start,
                Transaction.completed_at < hour_end,
            )
        )
        hourly_data.append({"hour": f"{hour:02d}:00", "processed": count_result.scalar() or 0})

    return APIResponse(success=True, data=MandiDashboard(
        centre_id=centre_id,
        centre_name=centre.name,
        date=today.isoformat(),
        daily_capacity=centre.daily_capacity,
        total_bookings=total_bookings,
        arrived_count=arrived,
        completed_count=completed,
        current_queue_size=queue_size,
        avg_processing_time_minutes=centre.avg_processing_time_minutes,
        quality_pending_count=quality_pending_count,
        payment_pending_count=payment_pending_count,
        active_grievances_count=active_grievances,
        hourly_throughput=hourly_data,
    ))


@mandi_router.get("/{centre_id}/alerts", response_model=APIResponse[list[AlertLogResponse]])
async def get_centre_alerts(
    centre_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    result = await db.execute(
        select(AlertLog)
        .where(
            AlertLog.centre_id == centre_id,
            AlertLog.is_acknowledged == False,
        )
        .order_by(AlertLog.severity.desc(), AlertLog.created_at.desc())
    )
    alerts = result.scalars().all()

    centre_result = await db.execute(
        select(ProcurementCentre).where(ProcurementCentre.id == centre_id)
    )
    centre = centre_result.scalar_one_or_none()

    enriched = []
    for a in alerts:
        resp = AlertLogResponse.model_validate(a)
        resp.centre_name = centre.name if centre else None
        enriched.append(resp)

    return APIResponse(success=True, data=enriched)


@mandi_router.put("/{centre_id}/alerts/{alert_id}/acknowledge", response_model=APIResponse[dict])
async def acknowledge_alert(
    centre_id: uuid.UUID,
    alert_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    result = await db.execute(
        select(AlertLog).where(AlertLog.id == alert_id, AlertLog.centre_id == centre_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_acknowledged = True
    await db.commit()
    return APIResponse(success=True, data={"message": "Alert acknowledged"})


# ─── Govt Dashboard ───────────────────────────────────────────────────────────

@govt_router.get("/", response_model=APIResponse[GovtDashboard])
async def get_govt_dashboard(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.GOVT_ADMIN, UserRole.MANDI_OFFICER]))],
):
    farmers_count = await db.execute(
        select(func.count()).where(User.role == UserRole.FARMER)
    )
    total_farmers = farmers_count.scalar() or 0

    txn_result = await db.execute(select(Transaction))
    txns = txn_result.scalars().all()
    total_q = sum(t.net_weight_q or 0 for t in txns)
    completed_q = sum(
        t.net_weight_q or 0 for t in txns
        if t.procurement_status == ProcurementStatus.CONFIRMED
    )

    active_mandis = await db.execute(
        select(func.count()).where(ProcurementCentre.is_active == True)
    )
    active_mandis_count = active_mandis.scalar() or 0

    high_congestion = await db.execute(
        select(func.count()).where(
            AlertLog.type.in_(["CONGESTION"]),
            AlertLog.is_acknowledged == False,
            AlertLog.severity.in_([AlertSeverity.HIGH, AlertSeverity.CRITICAL]),
        )
    )

    open_grievances = await db.execute(
        select(func.count()).where(
            Grievance.status.in_([GrievanceStatus.OPEN, GrievanceStatus.UNDER_REVIEW])
        )
    )

    return APIResponse(success=True, data=GovtDashboard(
        total_farmers=total_farmers,
        total_procurement_q=round(total_q, 2),
        completed_q=round(completed_q, 2),
        pending_q=round(total_q - completed_q, 2),
        active_mandis=active_mandis_count,
        high_congestion_count=high_congestion.scalar() or 0,
        quality_delay_count=0,
        payment_delay_count=sum(
            1 for t in txns if t.payment_status == PaymentStatus.NOT_INITIATED
            and t.procurement_status == ProcurementStatus.CONFIRMED
        ),
        open_grievances=open_grievances.scalar() or 0,
    ))


@govt_router.get("/drilldown", response_model=APIResponse[list[DrilldownRow]])
async def drilldown(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.GOVT_ADMIN, UserRole.MANDI_OFFICER]))],
    level: str = Query("state", regex="^(state|district|centre)$"),
    parent: Optional[str] = Query(None),
):
    """Drilldown aggregation by state → district → centre."""
    centres_result = await db.execute(
        select(ProcurementCentre).where(ProcurementCentre.is_active == True)
    )
    all_centres = centres_result.scalars().all()

    rows: list[DrilldownRow] = []

    if level == "state":
        # Group by state
        state_map: dict[str, list] = {}
        for c in all_centres:
            state_map.setdefault(c.state, []).append(c)

        for state_name, centres in state_map.items():
            centre_ids = [c.id for c in centres]
            txn_result = await db.execute(
                select(Transaction).where(Transaction.centre_id.in_(centre_ids))
            )
            txns = txn_result.scalars().all()
            total_q = sum(t.net_weight_q or 0 for t in txns)
            confirmed_q = sum(
                t.net_weight_q or 0 for t in txns
                if t.procurement_status == ProcurementStatus.CONFIRMED
            )
            farmer_count = await db.execute(
                select(func.count(SlotBooking.farmer_id.distinct())).where(
                    SlotBooking.centre_id.in_(centre_ids)
                )
            )
            rows.append(DrilldownRow(
                name=state_name,
                total_farmers=farmer_count.scalar() or 0,
                procurement_q=round(total_q, 2),
                completed_pct=round(confirmed_q / total_q * 100, 1) if total_q > 0 else 0,
                congestion_status="normal",
            ))

    elif level == "district":
        for c in all_centres:
            if parent and c.state != parent:
                continue
            txn_result = await db.execute(
                select(Transaction).where(Transaction.centre_id == c.id)
            )
            txns = txn_result.scalars().all()
            total_q = sum(t.net_weight_q or 0 for t in txns)
            confirmed_q = sum(
                t.net_weight_q or 0 for t in txns
                if t.procurement_status == ProcurementStatus.CONFIRMED
            )
            rows.append(DrilldownRow(
                id=c.id,
                name=c.district,
                total_farmers=0,
                procurement_q=round(total_q, 2),
                completed_pct=round(confirmed_q / total_q * 100, 1) if total_q > 0 else 0,
                congestion_status="normal",
            ))

    elif level == "centre":
        for c in all_centres:
            if parent and c.district != parent:
                continue
            txn_result = await db.execute(
                select(Transaction).where(Transaction.centre_id == c.id)
            )
            txns = txn_result.scalars().all()
            total_q = sum(t.net_weight_q or 0 for t in txns)
            confirmed_q = sum(
                t.net_weight_q or 0 for t in txns
                if t.procurement_status == ProcurementStatus.CONFIRMED
            )
            rows.append(DrilldownRow(
                id=c.id,
                name=c.name,
                total_farmers=0,
                procurement_q=round(total_q, 2),
                completed_pct=round(confirmed_q / total_q * 100, 1) if total_q > 0 else 0,
                congestion_status="normal",
            ))

    return APIResponse(success=True, data=rows)


@govt_router.get("/anomalies", response_model=APIResponse[list[AnomalyFlag]])
async def get_anomaly_flags(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    result = await db.execute(
        select(AlertLog).where(
            AlertLog.type == "ANOMALY",
            AlertLog.is_acknowledged == False,
        ).order_by(AlertLog.created_at.desc())
    )
    alerts = result.scalars().all()
    flags = []
    for a in alerts:
        centre_result = await db.execute(
            select(ProcurementCentre).where(ProcurementCentre.id == a.centre_id)
        )
        centre = centre_result.scalar_one_or_none()
        flags.append(AnomalyFlag(
            centre_id=a.centre_id,
            centre_name=centre.name if centre else "Unknown",
            district=centre.district if centre else "Unknown",
            today_rejection_rate=0.0,
            rolling_avg_rate=0.0,
            severity=a.severity.value,
            created_at=a.created_at.isoformat() if a.created_at else "",
        ))
    return APIResponse(success=True, data=flags)
