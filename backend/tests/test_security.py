"""Tests for IVR signature enforcement (#1), seed endpoint auth (#3), and the
payment/centre guards on transactions (#11)."""
import base64
import hashlib
import hmac
import pytest

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.procurement_centre import ProcurementCentre
from app.models.crop import Crop
from app.models.user import User
from app.models.slot_booking import SlotBooking, BookingStatus
from tests.conftest import login, auth_header
from tests.seed_test_data import make_booking


class TestIVRSignature:
    async def test_open_in_demo_mode(self, client, monkeypatch):
        """No TWILIO_AUTH_TOKEN configured → demo mode permits requests."""
        monkeypatch.setattr("app.routers.ivr.TWILIO_AUTH_TOKEN", "")
        res = await client.post("/api/ivr/incoming")
        assert res.status_code == 200
        assert "<Response>" in res.text

    async def test_missing_signature_rejected(self, client, monkeypatch):
        monkeypatch.setattr("app.routers.ivr.TWILIO_AUTH_TOKEN", "test-auth-token")
        res = await client.post("/api/ivr/incoming")
        assert res.status_code == 403

    async def test_valid_signature_accepted(self, client, monkeypatch):
        token = "test-auth-token"
        monkeypatch.setattr("app.routers.ivr.TWILIO_AUTH_TOKEN", token)

        url = "http://testserver/api/ivr/incoming"
        form = {"From": "+919000000001", "To": "+9118001551"}
        data_str = url + "".join(f"{k}{v}" for k, v in sorted(form.items()))
        signature = base64.b64encode(
            hmac.new(token.encode(), data_str.encode(), hashlib.sha1).digest()
        ).decode()

        res = await client.post(
            "/api/ivr/incoming", data=form, headers={"X-Twilio-Signature": signature}
        )
        assert res.status_code == 200
        assert "<Response>" in res.text

    async def test_invalid_signature_rejected(self, client, monkeypatch):
        monkeypatch.setattr("app.routers.ivr.TWILIO_AUTH_TOKEN", "test-auth-token")
        res = await client.post(
            "/api/ivr/incoming",
            data={"From": "+919000000001"},
            headers={"X-Twilio-Signature": "bogus-signature=="},
        )
        assert res.status_code == 403

    async def test_grievance_endpoint_requires_signature(self, client, monkeypatch):
        """The previously unguarded grievance endpoint is now protected too."""
        monkeypatch.setattr("app.routers.ivr.TWILIO_AUTH_TOKEN", "test-auth-token")
        res = await client.post("/api/ivr/grievance", data={"Digits": "2", "From": "+919000000001"})
        assert res.status_code == 403


class TestSeedAuth:
    async def test_seed_requires_authentication(self, client):
        res = await client.post("/api/admin/seed/full")
        assert res.status_code == 401

    async def test_seed_rejects_non_admin(self, client):
        token = await login(client, "9000000001", "test123")  # farmer
        res = await client.post("/api/admin/seed/full", headers=auth_header(token))
        assert res.status_code == 403

    async def test_typed_seed_requires_authentication(self, client):
        res = await client.post("/api/admin/seed/centres-crops")
        assert res.status_code == 401


class TestTransactionCentreGuard:
    async def test_staff_cannot_create_transaction_at_other_centre(self, client):
        async with AsyncSessionLocal() as db:
            centre_b = (await db.scalars(
                select(ProcurementCentre).where(ProcurementCentre.name == "Test Mandi B")
            )).first()
            wheat = (await db.scalars(select(Crop).where(Crop.crop_code == "WHT"))).first()
            farmer_a = (await db.scalars(select(User).where(User.mobile == "9000000001"))).first()
            booking = make_booking(farmer_a, centre_b, wheat)
            db.add(booking)
            await db.commit()
            booking_id = booking.id

        staff_a = await login(client, "9000000011", "test123")
        res = await client.post(
            "/api/transactions/", json={"slot_booking_id": str(booking_id)},
            headers=auth_header(staff_a),
        )
        assert res.status_code == 403

    async def test_farmer_cannot_confirm_transaction(self, client):
        async with AsyncSessionLocal() as db:
            centre = (await db.scalars(
                select(ProcurementCentre).where(ProcurementCentre.name == "Test Mandi A")
            )).first()
            wheat = (await db.scalars(select(Crop).where(Crop.crop_code == "WHT"))).first()
            farmer_a = (await db.scalars(select(User).where(User.mobile == "9000000001"))).first()
            booking = make_booking(farmer_a, centre, wheat)
            db.add(booking)
            await db.flush()
            from app.models.transaction import Transaction
            txn = Transaction(
                id=__import__("uuid").uuid4(), slot_booking_id=booking.id,
                farmer_id=farmer_a.id, centre_id=centre.id, crop_id=wheat.id,
                msp_per_q=wheat.msp_per_quintal,
            )
            db.add(txn)
            await db.commit()
            txn_id = txn.id

        farmer_token = await login(client, "9000000001", "test123")
        res = await client.put(
            f"/api/transactions/{txn_id}/confirm", headers=auth_header(farmer_token)
        )
        assert res.status_code == 403
