"""Alert and anomaly detection service."""
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.transaction import Transaction, ProcurementStatus, QualityStatus
from app.models.slot_booking import SlotBooking
from app.models.procurement_centre import ProcurementCentre
from app.models.alert_log import AlertLog, AlertType, AlertSeverity
from app.models.notification import Notification, NotificationChannel
from app.models.user import User, UserRole
from app.database import AsyncSessionLocal
from app.socketio_server import emit_alert_new


class AlertService:
    """Business logic for delay, congestion, and anomaly checks."""

    async def check_delays(self) -> None:
        """Find transactions stuck in PENDING quality for >90 minutes and create alerts."""
        async with AsyncSessionLocal() as db:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=90)
            result = await db.execute(
                select(Transaction).where(
                    Transaction.procurement_status == ProcurementStatus.PENDING,
                    Transaction.quality_status == None,
                    Transaction.created_at < cutoff,
                )
            )
            stuck_txns = result.scalars().all()

            for txn in stuck_txns:
                # Avoid duplicate alerts within the last hour
                recent_alert = await db.execute(
                    select(AlertLog).where(
                        AlertLog.centre_id == txn.centre_id,
                        AlertLog.type == AlertType.DELAY,
                        AlertLog.created_at > datetime.now(timezone.utc) - timedelta(hours=1),
                    )
                )
                if recent_alert.scalar_one_or_none():
                    continue

                alert = AlertLog(
                    id=uuid.uuid4(),
                    centre_id=txn.centre_id,
                    type=AlertType.DELAY,
                    message=(
                        f"Transaction {txn.id} has been pending quality check for "
                        f">{int((datetime.now(timezone.utc) - txn.created_at).total_seconds() // 60)} minutes."
                    ),
                    severity=AlertSeverity.HIGH,
                )
                db.add(alert)
                await db.flush()

                # Notify mandi officers
                officers = await db.execute(
                    select(User).where(User.role == UserRole.MANDI_OFFICER)
                )
                for officer in officers.scalars().all():
                    notif = Notification(
                        id=uuid.uuid4(),
                        user_id=officer.id,
                        title="⚠️ Processing Delay Alert",
                        body=alert.message,
                        channel=NotificationChannel.APP,
                    )
                    db.add(notif)

                await emit_alert_new(str(txn.centre_id), {
                    "id": str(alert.id),
                    "type": alert.type.value,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "created_at": alert.created_at.isoformat() if alert.created_at else None,
                })

            await db.commit()
            print(f"[AlertService] Delay check complete. Found {len(stuck_txns)} delayed transactions.")

    async def check_congestion(self) -> None:
        """Flag centres where tomorrow's bookings exceed 85% of daily capacity."""
        async with AsyncSessionLocal() as db:
            tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).date()

            result = await db.execute(
                select(ProcurementCentre).where(ProcurementCentre.is_active == True)
            )
            centres = result.scalars().all()

            for centre in centres:
                count_result = await db.execute(
                    select(func.count()).where(
                        SlotBooking.centre_id == centre.id,
                        SlotBooking.slot_date == tomorrow,
                    )
                )
                booked = count_result.scalar() or 0
                if booked > 0.85 * centre.daily_capacity:
                    alert = AlertLog(
                        id=uuid.uuid4(),
                        centre_id=centre.id,
                        type=AlertType.CONGESTION,
                        message=(
                            f"{centre.name}: {booked}/{centre.daily_capacity} slots booked for tomorrow "
                            f"({round(booked/centre.daily_capacity*100)}% full)."
                        ),
                        severity=AlertSeverity.MEDIUM,
                    )
                    db.add(alert)
                    await emit_alert_new(str(centre.id), {
                        "type": AlertType.CONGESTION.value,
                        "message": alert.message,
                        "severity": AlertSeverity.MEDIUM.value,
                    })

            await db.commit()
            print("[AlertService] Congestion check complete.")

    async def check_anomalies(self) -> None:
        """Flag centres with today's rejection rate > 2× 7-day rolling average."""
        async with AsyncSessionLocal() as db:
            today = datetime.now(timezone.utc).date()
            week_ago = today - timedelta(days=7)

            result = await db.execute(
                select(ProcurementCentre).where(ProcurementCentre.is_active == True)
            )
            centres = result.scalars().all()

            for centre in centres:
                # Today's quality stats
                today_result = await db.execute(
                    select(Transaction).where(
                        Transaction.centre_id == centre.id,
                        Transaction.quality_status != None,
                        func.date(Transaction.created_at) == today,
                    )
                )
                today_txns = today_result.scalars().all()
                total_checks_today = len(today_txns)
                if total_checks_today < 10:
                    continue  # Not enough data

                rejected_today = sum(1 for t in today_txns if t.quality_status == QualityStatus.REJECTED)
                today_rate = rejected_today / total_checks_today

                # 7-day rolling average
                week_result = await db.execute(
                    select(Transaction).where(
                        Transaction.centre_id == centre.id,
                        Transaction.quality_status != None,
                        func.date(Transaction.created_at) >= week_ago,
                        func.date(Transaction.created_at) < today,
                    )
                )
                week_txns = week_result.scalars().all()
                total_week = len(week_txns)
                if total_week == 0:
                    continue

                rejected_week = sum(1 for t in week_txns if t.quality_status == QualityStatus.REJECTED)
                week_avg = rejected_week / total_week

                if today_rate > 2 * week_avg and week_avg > 0:
                    alert = AlertLog(
                        id=uuid.uuid4(),
                        centre_id=centre.id,
                        type=AlertType.ANOMALY,
                        message=(
                            f"{centre.name}: Today's rejection rate is {round(today_rate*100)}% "
                            f"vs 7-day avg of {round(week_avg*100)}%. "
                            f"Possible quality anomaly detected."
                        ),
                        severity=AlertSeverity.HIGH,
                    )
                    db.add(alert)
                    await emit_alert_new(str(centre.id), {
                        "type": AlertType.ANOMALY.value,
                        "message": alert.message,
                        "severity": AlertSeverity.HIGH.value,
                    })

            await db.commit()
            print("[AlertService] Anomaly detection complete.")
