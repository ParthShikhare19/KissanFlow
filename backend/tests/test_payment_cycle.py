"""Tests for the full procurement cycle: confirm keeps booking PROCESSING and
payment marks it COMPLETED (#12, #18), plus notifications (#14/#15)."""
import uuid as uuid_module

import pytest
from datetime import date

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.procurement_centre import ProcurementCentre
from app.models.crop import Crop
from app.models.user import User
from app.models.slot_booking import SlotBooking, BookingStatus
from app.models.queue_entry import QueueEntry, QueueStatus
from app.models.transaction import Transaction, QualityStatus, PaymentStatus, ProcurementStatus
from tests.conftest import login, auth_header
from tests.seed_test_data import make_booking


async def _ids():
    async with AsyncSessionLocal() as db:
        centre = (await db.scalars(
            select(ProcurementCentre).where(ProcurementCentre.name == "Test Mandi A")
        )).first()
        wheat = (await db.scalars(select(Crop).where(Crop.crop_code == "WHT"))).first()
        farmer_a = (await db.scalars(select(User).where(User.mobile == "9000000001"))).first()
    return centre, wheat, farmer_a


async def _add(*rows):
    async with AsyncSessionLocal() as db:
        for r in rows:
            db.add(r)
        await db.commit()


async def _get_booking(booking_id):
    async with AsyncSessionLocal() as db:
        return (await db.scalars(
            select(SlotBooking).where(SlotBooking.id == booking_id)
        )).first()


async def _get_txn(txn_id):
    async with AsyncSessionLocal() as db:
        return (await db.scalars(
            select(Transaction).where(Transaction.id == uuid_module.UUID(str(txn_id)))
        )).first()


@pytest.fixture
async def tokens(client):
    return {
        "staff_a": await login(client, "9000000011", "test123"),
        "officer_a": await login(client, "9000000021", "test123"),
        "govt": await login(client, "9000000031", "test123"),
        "farmer_a": await login(client, "9000000001", "test123"),
    }


async def _drive_to_confirmed(client, tokens) -> tuple:
    """Create a booking, admit it at the gate, and confirm the transaction."""
    centre, wheat, farmer_a = await _ids()
    booking = make_booking(farmer_a, centre, wheat, slot_date=date.today())
    await _add(booking)

    r = await client.post(
        "/api/queue/gate-entry", json={"token_number": booking.token_number},
        headers=auth_header(tokens["staff_a"]),
    )
    assert r.status_code == 200, r.text

    r = await client.post(
        "/api/transactions/", json={"slot_booking_id": str(booking.id)},
        headers=auth_header(tokens["staff_a"]),
    )
    assert r.status_code == 201, r.text
    txn_id = r.json()["data"]["id"]

    r = await client.put(
        f"/api/transactions/{txn_id}/quality",
        json={"moisture_percent": 10.5, "foreign_matter_percent": 0.5,
              "quality_status": "ACCEPTED"},
        headers=auth_header(tokens["staff_a"]),
    )
    assert r.status_code == 200, r.text

    r = await client.put(
        f"/api/transactions/{txn_id}/weighment",
        json={"gross_weight_q": 30.0, "tare_weight_q": 2.0},
        headers=auth_header(tokens["staff_a"]),
    )
    assert r.status_code == 200, r.text

    r = await client.put(
        f"/api/transactions/{txn_id}/confirm", headers=auth_header(tokens["officer_a"])
    )
    assert r.status_code == 200, r.text
    return booking, txn_id


class TestPaymentBeforeComplete:
    async def test_confirm_keeps_booking_processing(self, client, tokens):
        booking, txn_id = await _drive_to_confirmed(client, tokens)
        b = await _get_booking(booking.id)
        assert b.status == BookingStatus.PROCESSING
        txn = await _get_txn(txn_id)
        assert txn.procurement_status == ProcurementStatus.CONFIRMED
        assert txn.payment_status == PaymentStatus.NOT_INITIATED
        assert txn.confirmed_at is not None

    async def test_payment_completes_booking(self, client, tokens):
        booking, txn_id = await _drive_to_confirmed(client, tokens)
        r = await client.put(
            f"/api/transactions/{txn_id}/payment", headers=auth_header(tokens["officer_a"])
        )
        assert r.status_code == 200, r.text
        b = await _get_booking(booking.id)
        assert b.status == BookingStatus.COMPLETED
        txn = await _get_txn(txn_id)
        assert txn.payment_status == PaymentStatus.PAID
        assert txn.paid_at is not None

    async def test_dashboard_resets_after_payment(self, client, tokens):
        """#13: after a fully paid cycle, no 'active' booking remains."""
        booking, txn_id = await _drive_to_confirmed(client, tokens)
        await client.put(
            f"/api/transactions/{txn_id}/payment", headers=auth_header(tokens["officer_a"])
        )
        res = await client.get(
            f"/api/farmers/{booking.farmer_id}/bookings/latest",
            headers=auth_header(tokens["farmer_a"]),
        )
        assert res.status_code == 200
        assert res.json()["data"] is None


class TestStageTimestamps:
    async def test_stage_timestamps_are_persisted(self, client, tokens):
        """#18: every stage records its own timestamp."""
        booking, txn_id = await _drive_to_confirmed(client, tokens)
        await client.put(
            f"/api/transactions/{txn_id}/payment", headers=auth_header(tokens["officer_a"])
        )
        txn = await _get_txn(txn_id)
        assert txn.quality_done_at is not None
        assert txn.weighment_done_at is not None
        assert txn.confirmed_at is not None
        assert txn.payment_initiated_at is not None
        assert txn.paid_at is not None
        # Ordering sanity
        assert txn.quality_done_at <= txn.weighment_done_at <= txn.confirmed_at

    async def test_process_summary_uses_stage_timestamps(self, client, tokens):
        booking, txn_id = await _drive_to_confirmed(client, tokens)
        await client.put(
            f"/api/transactions/{txn_id}/payment", headers=auth_header(tokens["officer_a"])
        )
        res = await client.get(
            f"/api/farmers/{booking.farmer_id}/process-summary",
            headers=auth_header(tokens["farmer_a"]),
        )
        assert res.status_code == 200
        row = next(
            r for r in res.json()["data"] if r["booking_id"] == str(booking.id)
        )
        assert row["processing_to_completion_minutes"] is not None
        assert row["total_cycle_minutes"] is not None


class TestNotifications:
    async def test_unread_count_and_read_all(self, client, tokens):
        farmer_a = (await _ids())[2]
        from app.models.notification import Notification, NotificationChannel
        rows = [
            Notification(id=__import__("uuid").uuid4(), user_id=farmer_a.id,
                         title=f"N{i}", body="body", channel=NotificationChannel.APP)
            for i in range(7)
        ]
        await _add(*rows)

        res = await client.get(
            f"/api/notifications/{farmer_a.id}/unread-count",
            headers=auth_header(tokens["farmer_a"]),
        )
        assert res.status_code == 200
        assert res.json()["data"]["unread_count"] == 7

        res = await client.put(
            f"/api/notifications/{farmer_a.id}/read-all",
            headers=auth_header(tokens["farmer_a"]),
        )
        assert res.status_code == 200
        assert res.json()["data"]["marked_read"] == 7

        res = await client.get(
            f"/api/notifications/{farmer_a.id}/unread-count",
            headers=auth_header(tokens["farmer_a"]),
        )
        assert res.json()["data"]["unread_count"] == 0

    async def test_other_user_cannot_read_all(self, client, tokens):
        farmer_a = (await _ids())[2]
        res = await client.put(
            f"/api/notifications/{farmer_a.id}/read-all",
            headers=auth_header(tokens["govt"]),
        )
        # GOVT_ADMIN is allowed by design (oversight).
        assert res.status_code == 200
        farmer_b_token = await login(client, "9000000002", "test123")
        res = await client.put(
            f"/api/notifications/{farmer_a.id}/read-all",
            headers=auth_header(farmer_b_token),
        )
        assert res.status_code == 403
