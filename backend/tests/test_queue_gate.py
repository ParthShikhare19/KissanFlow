"""Tests for gate-entry admission rules (#4), centre scoping (#10/#11), and
queue position visibility (#7)."""
import pytest
from datetime import date, timedelta

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.procurement_centre import ProcurementCentre
from app.models.crop import Crop
from app.models.slot_booking import SlotBooking, BookingStatus
from app.models.user import User
from tests.conftest import login, auth_header
from tests.seed_test_data import make_booking


async def _ids():
    async with AsyncSessionLocal() as db:
        centre_a = (await db.scalars(
            select(ProcurementCentre).where(ProcurementCentre.name == "Test Mandi A")
        )).first()
        centre_b = (await db.scalars(
            select(ProcurementCentre).where(ProcurementCentre.name == "Test Mandi B")
        )).first()
        wheat = (await db.scalars(select(Crop).where(Crop.crop_code == "WHT"))).first()
        farmer_a = (await db.scalars(select(User).where(User.mobile == "9000000001"))).first()
    return centre_a, centre_b, wheat, farmer_a


async def _add_booking(booking):
    async with AsyncSessionLocal() as db:
        db.add(booking)
        await db.commit()


@pytest.fixture
async def staff_tokens(client):
    return {
        "staff_a": await login(client, "9000000011", "test123"),
        "staff_b": await login(client, "9000000012", "test123"),
    }


class TestGateEntry:
    async def test_today_booking_admitted(self, client, staff_tokens):
        centre_a, _, wheat, farmer_a = await _ids()
        booking = make_booking(farmer_a, centre_a, wheat, status=BookingStatus.BOOKED,
                               slot_date=date.today())
        await _add_booking(booking)
        res = await client.post(
            "/api/queue/gate-entry", json={"token_number": booking.token_number},
            headers=auth_header(staff_tokens["staff_a"]),
        )
        assert res.status_code == 200, res.text
        async with AsyncSessionLocal() as db:
            b = (await db.scalars(
                select(SlotBooking).where(SlotBooking.id == booking.id)
            )).first()
        assert b.status == BookingStatus.IN_QUEUE

    async def test_future_booking_rejected(self, client, staff_tokens):
        centre_a, _, wheat, farmer_a = await _ids()
        booking = make_booking(farmer_a, centre_a, wheat,
                               slot_date=date.today() + timedelta(days=3))
        await _add_booking(booking)
        res = await client.post(
            "/api/queue/gate-entry", json={"token_number": booking.token_number},
            headers=auth_header(staff_tokens["staff_a"]),
        )
        assert res.status_code == 400
        assert "future" in res.text.lower()

    async def test_past_booking_rejected(self, client, staff_tokens):
        centre_a, _, wheat, farmer_a = await _ids()
        booking = make_booking(farmer_a, centre_a, wheat,
                               slot_date=date.today() - timedelta(days=1))
        await _add_booking(booking)
        res = await client.post(
            "/api/queue/gate-entry", json={"token_number": booking.token_number},
            headers=auth_header(staff_tokens["staff_a"]),
        )
        assert res.status_code == 400

    async def test_completed_booking_rejected(self, client, staff_tokens):
        centre_a, _, wheat, farmer_a = await _ids()
        booking = make_booking(farmer_a, centre_a, wheat, status=BookingStatus.COMPLETED,
                               slot_date=date.today())
        await _add_booking(booking)
        res = await client.post(
            "/api/queue/gate-entry", json={"token_number": booking.token_number},
            headers=auth_header(staff_tokens["staff_a"]),
        )
        assert res.status_code == 400
        assert "completed" in res.text.lower()

    async def test_no_show_booking_rejected(self, client, staff_tokens):
        centre_a, _, wheat, farmer_a = await _ids()
        booking = make_booking(farmer_a, centre_a, wheat, status=BookingStatus.NO_SHOW,
                               slot_date=date.today())
        await _add_booking(booking)
        res = await client.post(
            "/api/queue/gate-entry", json={"token_number": booking.token_number},
            headers=auth_header(staff_tokens["staff_a"]),
        )
        assert res.status_code == 400
        assert "no-show" in res.text.lower()

    async def test_cancelled_booking_rejected(self, client, staff_tokens):
        centre_a, _, wheat, farmer_a = await _ids()
        booking = make_booking(farmer_a, centre_a, wheat, status=BookingStatus.CANCELLED,
                               slot_date=date.today())
        await _add_booking(booking)
        res = await client.post(
            "/api/queue/gate-entry", json={"token_number": booking.token_number},
            headers=auth_header(staff_tokens["staff_a"]),
        )
        assert res.status_code == 400
        assert "cancelled" in res.text.lower()

    async def test_gate_entry_is_idempotent(self, client, staff_tokens):
        centre_a, _, wheat, farmer_a = await _ids()
        booking = make_booking(farmer_a, centre_a, wheat, slot_date=date.today())
        await _add_booking(booking)
        r1 = await client.post(
            "/api/queue/gate-entry", json={"token_number": booking.token_number},
            headers=auth_header(staff_tokens["staff_a"]),
        )
        r2 = await client.post(
            "/api/queue/gate-entry", json={"token_number": booking.token_number},
            headers=auth_header(staff_tokens["staff_a"]),
        )
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["data"]["id"] == r2.json()["data"]["id"]


class TestCentreScoping:
    async def test_staff_cannot_admit_other_centre_booking(self, client, staff_tokens):
        centre_a, centre_b, wheat, farmer_a = await _ids()
        booking = make_booking(farmer_a, centre_b, wheat, slot_date=date.today())
        await _add_booking(booking)
        res = await client.post(
            "/api/queue/gate-entry", json={"token_number": booking.token_number},
            headers=auth_header(staff_tokens["staff_a"]),  # assigned to centre A
        )
        assert res.status_code == 403

    async def test_staff_cannot_read_other_centre_queue(self, client, staff_tokens):
        _, centre_b, _, _ = await _ids()
        res = await client.get(
            f"/api/queue/{centre_b.id}", headers=auth_header(staff_tokens["staff_a"])
        )
        assert res.status_code == 403

    async def test_farmer_can_read_own_queue_position(self, client, staff_tokens):
        centre_a, _, wheat, farmer_a = await _ids()
        booking = make_booking(farmer_a, centre_a, wheat, slot_date=date.today())
        await _add_booking(booking)
        await client.post(
            "/api/queue/gate-entry", json={"token_number": booking.token_number},
            headers=auth_header(staff_tokens["staff_a"]),
        )
        farmer_token = await login(client, "9000000001", "test123")
        res = await client.get(
            f"/api/queue/position/{booking.id}", headers=auth_header(farmer_token)
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["position"] == 1
        assert data["ahead_of_you"] == 0

    async def test_farmer_cannot_read_others_queue_position(self, client, staff_tokens):
        centre_a, _, wheat, farmer_a = await _ids()
        booking = make_booking(farmer_a, centre_a, wheat, slot_date=date.today())
        await _add_booking(booking)
        await client.post(
            "/api/queue/gate-entry", json={"token_number": booking.token_number},
            headers=auth_header(staff_tokens["staff_a"]),
        )
        farmer_b_token = await login(client, "9000000002", "test123")
        res = await client.get(
            f"/api/queue/position/{booking.id}", headers=auth_header(farmer_b_token)
        )
        assert res.status_code == 403
