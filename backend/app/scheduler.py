"""APScheduler background jobs for AnnSetu alerts and anomaly detection."""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.services.alert_service import AlertService

scheduler = AsyncIOScheduler()
_alert_service = AlertService()


def setup_scheduler() -> AsyncIOScheduler:
    """Configure and return the APScheduler instance with all jobs."""

    # Job 1: Delay check — every 5 minutes
    scheduler.add_job(
        _alert_service.check_delays,
        trigger=IntervalTrigger(minutes=5),
        id="delay_check",
        name="Check for processing delays",
        replace_existing=True,
        misfire_grace_time=60,
    )

    # Job 2: Congestion check — every hour
    scheduler.add_job(
        _alert_service.check_congestion,
        trigger=IntervalTrigger(hours=1),
        id="congestion_check",
        name="Check for upcoming congestion",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Job 3: Anomaly detection — once daily at 6 PM IST
    scheduler.add_job(
        _alert_service.check_anomalies,
        trigger=CronTrigger(hour=18, minute=0, timezone="Asia/Kolkata"),
        id="anomaly_detection",
        name="Daily anomaly detection",
        replace_existing=True,
        misfire_grace_time=600,
    )

    return scheduler
