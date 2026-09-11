"""Deterministic baseline data for the test suite."""
import uuid
import json
from datetime import date, time, datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.procurement_centre import ProcurementCentre
from app.models.crop import Crop, CropSeason
from app.models.user import User, UserRole
from app.models.farmer_profile import FarmerProfile
from app.models.slot_booking import SlotBooking, BookingStatus
from app.utils.security import hash_password

TODAY = date.today()


async def seed_baseline(db: AsyncSession) -> dict:
    """Insert two centres, one crop, and the users used by every test."""
    centre_a = ProcurementCentre(
        id=uuid.uuid4(), name="Test Mandi A", district="Ludhiana", state="Punjab",
        latitude=30.9, longitude=75.8, daily_capacity=150, avg_processing_time_minutes=20,
        is_active=True,
    )
    centre_b = ProcurementCentre(
        id=uuid.uuid4(), name="Test Mandi B", district="Amritsar", state="Punjab",
        latitude=31.6, longitude=74.8, daily_capacity=120, avg_processing_time_minutes=25,
        is_active=True,
    )
    wheat = Crop(
        id=uuid.uuid4(), name="Wheat", season=CropSeason.RABI,
        msp_per_quintal=2275, crop_code="WHT",
    )
    rice = Crop(
        id=uuid.uuid4(), name="Rice", season=CropSeason.KHARIF,
        msp_per_quintal=2300, crop_code="RIC",
    )
    db.add_all([centre_a, centre_b, wheat, rice])
    await db.flush()

    def make_user(name, mobile, role, password="test123", centre=None):
        return User(
            id=uuid.uuid4(), name=name, mobile=mobile, role=role,
            password_hash=hash_password(password), assigned_centre_id=centre,
        )

    farmer_a = make_user("Farmer A", "9000000001", UserRole.FARMER)
    farmer_b = make_user("Farmer B", "9000000002", UserRole.FARMER)
    staff_a = make_user("Staff A", "9000000011", UserRole.MANDI_STAFF, centre=centre_a.id)
    staff_b = make_user("Staff B", "9000000012", UserRole.MANDI_STAFF, centre=centre_b.id)
    officer_a = make_user("Officer A", "9000000021", UserRole.MANDI_OFFICER, centre=centre_a.id)
    govt = make_user("Govt Admin", "9000000031", UserRole.GOVT_ADMIN)
    db.add_all([farmer_a, farmer_b, staff_a, staff_b, officer_a, govt])
    await db.flush()

    db.add(FarmerProfile(
        id=uuid.uuid4(), user_id=farmer_a.id, village="Village A",
        district="Ludhiana", state="Punjab", land_holding=4.0,
        bank_account_number_encrypted="XXXX1111", bank_ifsc_code="PUNB0000001",
    ))
    await db.flush()

    return {
        "centre_a": centre_a, "centre_b": centre_b,
        "wheat": wheat, "rice": rice,
        "farmer_a": farmer_a, "farmer_b": farmer_b,
        "staff_a": staff_a, "staff_b": staff_b,
        "officer_a": officer_a, "govt": govt,
    }


def make_booking(
    farmer, centre, crop,
    status=BookingStatus.BOOKED,
    slot_date=None,
    token=None,
    declared=25.0,
    created_hours_ago=2,
) -> SlotBooking:
    """Build a booking row directly (bypasses the API for scenario setup)."""
    slot_date = slot_date or TODAY
    slot_start = time(10, 0)
    token = token or f"TST-{uuid.uuid4().hex[:8].upper()}"
    qr_data = {
        "token": token, "farmer_id": str(farmer.id), "centre_id": str(centre.id),
        "slot_date": slot_date.isoformat(), "slot_start": "10:00", "crop_id": str(crop.id),
    }
    return SlotBooking(
        id=uuid.uuid4(), farmer_id=farmer.id, centre_id=centre.id, crop_id=crop.id,
        slot_date=slot_date, slot_start_time=slot_start, slot_end_time=time(10, 20),
        token_number=token, qr_code_data=json.dumps(qr_data), status=status,
        declared_quantity_q=declared,
        created_at=datetime.now(timezone.utc) - timedelta(hours=created_hours_ago),
    )
