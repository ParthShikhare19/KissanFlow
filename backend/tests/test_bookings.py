"""Tests for booking creation validation and slot allocation (#8, #9)."""
import pytest
from tests.conftest import login, auth_header
from tests.seed_test_data import make_booking

from app.database import AsyncSessionLocal


@pytest.fixture
async def tokens(client):
    return {
        "farmer_a": await login(client, "9000000001", "test123"),
        "farmer_b": await login(client, "9000000002", "test123"),
    }


@pytest.fixture
async def ids():
    from tests.seed_test_data import seed_baseline  # noqa: F401  (already seeded by fixture)
    from app.models.procurement_centre import ProcurementCentre
    from app.models.crop import Crop
    async with AsyncSessionLocal() as db:
        centre = (await db.scalars(
            __import__("sqlalchemy").select(ProcurementCentre)
            .where(ProcurementCentre.name == "Test Mandi A")
        )).first()
        wheat = (await db.scalars(
            __import__("sqlalchemy").select(Crop).where(Crop.crop_code == "WHT")
        )).first()
    return {"centre_id": str(centre.id), "crop_id": str(wheat.id)}


class TestBookingValidation:
    async def test_zero_quantity_rejected(self, client, tokens, ids):
        res = await client.post(
            "/api/bookings/",
            json={
                "centre_id": ids["centre_id"], "crop_id": ids["crop_id"],
                "preferred_date": "2030-01-15", "declared_quantity_q": 0,
            },
            headers=auth_header(tokens["farmer_a"]),
        )
        assert res.status_code == 422

    async def test_negative_quantity_rejected(self, client, tokens, ids):
        res = await client.post(
            "/api/bookings/",
            json={
                "centre_id": ids["centre_id"], "crop_id": ids["crop_id"],
                "preferred_date": "2030-01-15", "declared_quantity_q": -5,
            },
            headers=auth_header(tokens["farmer_a"]),
        )
        assert res.status_code == 422

    async def test_quantity_above_500_rejected(self, client, tokens, ids):
        res = await client.post(
            "/api/bookings/",
            json={
                "centre_id": ids["centre_id"], "crop_id": ids["crop_id"],
                "preferred_date": "2030-01-15", "declared_quantity_q": 501,
            },
            headers=auth_header(tokens["farmer_a"]),
        )
        assert res.status_code == 422

    async def test_past_date_rejected(self, client, tokens, ids):
        res = await client.post(
            "/api/bookings/",
            json={
                "centre_id": ids["centre_id"], "crop_id": ids["crop_id"],
                "preferred_date": "2020-01-15", "declared_quantity_q": 25,
            },
            headers=auth_header(tokens["farmer_a"]),
        )
        assert res.status_code == 422
        assert "past" in res.text.lower()

    async def test_valid_booking_created(self, client, tokens, ids):
        from datetime import date, timedelta
        res = await client.post(
            "/api/bookings/",
            json={
                "centre_id": ids["centre_id"], "crop_id": ids["crop_id"],
                "preferred_date": (date.today() + timedelta(days=1)).isoformat(),
                "declared_quantity_q": 25,
            },
            headers=auth_header(tokens["farmer_a"]),
        )
        assert res.status_code == 201, res.text
        data = res.json()["data"]
        assert data["token_number"].startswith("WHT-")
        assert data["qr_code_base64"]


class TestSlotAllocation:
    async def _book(self, client, token, ids, day):
        from datetime import date, timedelta
        return await client.post(
            "/api/bookings/",
            json={
                "centre_id": ids["centre_id"], "crop_id": ids["crop_id"],
                "preferred_date": (date.today() + timedelta(days=day)).isoformat(),
                "declared_quantity_q": 10,
            },
            headers=auth_header(token),
        )

    async def test_tokens_are_unique(self, client, tokens, ids):
        r1 = await self._book(client, tokens["farmer_a"], ids, 1)
        r2 = await self._book(client, tokens["farmer_b"], ids, 1)
        assert r1.status_code == 201 and r2.status_code == 201
        t1 = r1.json()["data"]["token_number"]
        t2 = r2.json()["data"]["token_number"]
        assert t1 != t2

    async def test_capacity_moves_to_next_slot(self, client, tokens, ids):
        """Fill one slot past capacity; the next booking lands in a later slot."""
        from sqlalchemy import select
        from app.models.slot_booking import SlotBooking
        responses = [
            await self._book(client, tokens["farmer_a"], ids, 1) for _ in range(8)
        ]
        assert all(r.status_code == 201 for r in responses)

        async with AsyncSessionLocal() as db:
            bookings = (await db.scalars(select(SlotBooking))).all()
        start_times = sorted({b.slot_start_time.strftime("%H:%M") for b in bookings})
        # Per-slot capacity for this centre is 150 // 24 = 6, so 8 bookings
        # must occupy at least two distinct slots.
        assert len(start_times) >= 2
