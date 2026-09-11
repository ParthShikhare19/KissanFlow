"""Tests for farmer-data ownership (#2) and the booking-selection priority
(#5/#13/#19)."""
import pytest
from datetime import date, timedelta

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.procurement_centre import ProcurementCentre
from app.models.crop import Crop
from app.models.user import User
from app.models.slot_booking import SlotBooking, BookingStatus
from tests.conftest import login, auth_header
from tests.seed_test_data import make_booking


async def _ids():
    async with AsyncSessionLocal() as db:
        centre = (await db.scalars(
            select(ProcurementCentre).where(ProcurementCentre.name == "Test Mandi A")
        )).first()
        wheat = (await db.scalars(select(Crop).where(Crop.crop_code == "WHT"))).first()
        farmer_a = (await db.scalars(select(User).where(User.mobile == "9000000001"))).first()
        farmer_b = (await db.scalars(select(User).where(User.mobile == "9000000002"))).first()
    return centre, wheat, farmer_a, farmer_b


async def _add_booking(booking):
    async with AsyncSessionLocal() as db:
        db.add(booking)
        await db.commit()


@pytest.fixture
async def farmer_tokens(client):
    return {
        "farmer_a": await login(client, "9000000001", "test123"),
        "farmer_b": await login(client, "9000000002", "test123"),
    }


class TestFarmerOwnership:
    @pytest.mark.parametrize("path_suffix", [
        "profile", "timeline", "transactions", "grievances", "notifications",
        "bookings/latest", "process-summary",
    ])
    async def test_farmer_cannot_read_other_farmer(self, client, farmer_tokens, path_suffix):
        _, _, farmer_a, _ = await _ids()
        res = await client.get(
            f"/api/farmers/{farmer_a.id}/{path_suffix.strip('/')}",
            headers=auth_header(farmer_tokens["farmer_b"]),
        )
        assert res.status_code == 403

    async def test_farmer_can_read_own_data(self, client, farmer_tokens):
        _, _, farmer_a, _ = await _ids()
        for path_suffix in ["profile", "timeline", "transactions", "grievances",
                            "notifications", "bookings/latest", "process-summary"]:
            res = await client.get(
                f"/api/farmers/{farmer_a.id}/{path_suffix.strip('/')}",
                headers=auth_header(farmer_tokens["farmer_a"]),
            )
            assert res.status_code == 200, f"{path_suffix}: {res.text}"


class TestBookingSelection:
    async def test_active_booking_not_hidden_by_future_booking(self, client, farmer_tokens):
        """#5: an in-queue booking must win over a newly booked future slot."""
        centre, wheat, farmer_a, _ = await _ids()
        active = make_booking(farmer_a, centre, wheat, status=BookingStatus.IN_QUEUE,
                              slot_date=date.today())
        future = make_booking(farmer_a, centre, wheat, status=BookingStatus.BOOKED,
                              slot_date=date.today() + timedelta(days=5))
        await _add_booking(active)
        await _add_booking(future)

        res = await client.get(
            f"/api/farmers/{farmer_a.id}/bookings/latest",
            headers=auth_header(farmer_tokens["farmer_a"]),
        )
        assert res.status_code == 200
        assert res.json()["data"]["id"] == str(active.id)

    async def test_processing_wins_over_in_queue(self, client, farmer_tokens):
        centre, wheat, farmer_a, _ = await _ids()
        queued = make_booking(farmer_a, centre, wheat, status=BookingStatus.IN_QUEUE,
                              slot_date=date.today())
        processing = make_booking(farmer_a, centre, wheat, status=BookingStatus.PROCESSING,
                                  slot_date=date.today())
        await _add_booking(queued)
        await _add_booking(processing)

        res = await client.get(
            f"/api/farmers/{farmer_a.id}/bookings/latest",
            headers=auth_header(farmer_tokens["farmer_a"]),
        )
        assert res.json()["data"]["id"] == str(processing.id)

    async def test_upcoming_booked_wins_over_old_completed(self, client, farmer_tokens):
        centre, wheat, farmer_a, _ = await _ids()
        completed = make_booking(farmer_a, centre, wheat, status=BookingStatus.COMPLETED,
                                 slot_date=date.today() - timedelta(days=2))
        upcoming = make_booking(farmer_a, centre, wheat, status=BookingStatus.BOOKED,
                                slot_date=date.today())
        await _add_booking(completed)
        await _add_booking(upcoming)

        res = await client.get(
            f"/api/farmers/{farmer_a.id}/bookings/latest",
            headers=auth_header(farmer_tokens["farmer_a"]),
        )
        assert res.json()["data"]["id"] == str(upcoming.id)
