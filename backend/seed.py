"""
AnnSetu — Database Seed Script
Run: python seed.py

Inserts demo data in correct FK order.
Prints all credentials at the end.
"""
import asyncio
import uuid
from datetime import date, time, datetime, timezone, timedelta
import random
from sqlalchemy import select

from dotenv import load_dotenv
load_dotenv()

from app.database import AsyncSessionLocal, engine
from app.database import Base
from app.models import *
from app.utils.security import hash_password
from app.utils.qr_generator import generate_qr_base64
import json


async def run_seed(db=None):
    close_db = False
    if db is None:
        db = AsyncSessionLocal()
        close_db = True

    # ── 1. Procurement Centres ────────────────────────────────────────────────
    centres_data = [
        {"name": "Ludhiana Mandi A", "district": "Ludhiana", "state": "Punjab",
         "latitude": 30.9010, "longitude": 75.8573, "daily_capacity": 150, "avg_processing_time_minutes": 20},
        {"name": "Amritsar Grain Centre", "district": "Amritsar", "state": "Punjab",
         "latitude": 31.6340, "longitude": 74.8723, "daily_capacity": 120, "avg_processing_time_minutes": 25},
        {"name": "Karnal Procurement Hub", "district": "Karnal", "state": "Haryana",
         "latitude": 29.6857, "longitude": 76.9905, "daily_capacity": 180, "avg_processing_time_minutes": 15},
        {"name": "Agra Central Mandi", "district": "Agra", "state": "Uttar Pradesh",
         "latitude": 27.1767, "longitude": 78.0081, "daily_capacity": 200, "avg_processing_time_minutes": 20},
        {"name": "Varanasi Annadata Centre", "district": "Varanasi", "state": "Uttar Pradesh",
         "latitude": 25.3176, "longitude": 82.9739, "daily_capacity": 100, "avg_processing_time_minutes": 30},
    ]
    centres = []
    for c_data in centres_data:
        c = ProcurementCentre(id=uuid.uuid4(), **c_data, is_active=True)
        db.add(c)
        centres.append(c)
    await db.flush()
    print(f"[OK] Inserted {len(centres)} procurement centres")

    # ── 2. Crops ───────────────────────────────────────────────────────────────
    crops_data = [
        {"name": "Wheat",    "season": CropSeason.RABI,   "msp_per_quintal": 2275, "crop_code": "WHT"},
        {"name": "Rice",     "season": CropSeason.KHARIF, "msp_per_quintal": 2300, "crop_code": "RIC"},
        {"name": "Maize",    "season": CropSeason.KHARIF, "msp_per_quintal": 2090, "crop_code": "MAZ"},
        {"name": "Mustard",  "season": CropSeason.RABI,   "msp_per_quintal": 5650, "crop_code": "MST"},
        {"name": "Soybean",  "season": CropSeason.KHARIF, "msp_per_quintal": 4892, "crop_code": "SOY"},
        {"name": "Cotton",   "season": CropSeason.KHARIF, "msp_per_quintal": 7121, "crop_code": "COT"},
    ]
    crops = []
    for cr_data in crops_data:
        cr = Crop(id=uuid.uuid4(), **cr_data)
        db.add(cr)
        crops.append(cr)
    await db.flush()
    print(f"[OK] Inserted {len(crops)} crops")

    # ── 3. Users ───────────────────────────────────────────────────────────────
    # 3 farmers, 3 staff, 3 officers, 3 govt admins, 3 CSC operators = 15 users
    demo_users = [
        # Farmers
        {"name": "Ranjit Singh",    "mobile": "9876543210", "role": UserRole.FARMER,       "password": "farmer123"},
        {"name": "Meera Devi",      "mobile": "9876543211", "role": UserRole.FARMER,       "password": "farmer123"},
        {"name": "Suresh Kumar",    "mobile": "9876543212", "role": UserRole.FARMER,       "password": "farmer123"},
        # Mandi Staff
        {"name": "Amit Sharma",     "mobile": "9876543220", "role": UserRole.MANDI_STAFF,  "password": "staff123"},
        {"name": "Priya Verma",     "mobile": "9876543221", "role": UserRole.MANDI_STAFF,  "password": "staff123"},
        {"name": "Deepak Yadav",    "mobile": "9876543222", "role": UserRole.MANDI_STAFF,  "password": "staff123"},
        # Mandi Officers
        {"name": "Rajesh Gupta",    "mobile": "9876543230", "role": UserRole.MANDI_OFFICER,"password": "officer123"},
        {"name": "Sunita Pandey",   "mobile": "9876543231", "role": UserRole.MANDI_OFFICER,"password": "officer123"},
        {"name": "Vivek Mishra",    "mobile": "9876543232", "role": UserRole.MANDI_OFFICER,"password": "officer123"},
        # Govt Admins
        {"name": "Dr. A.K. Singh",  "mobile": "9876543240", "role": UserRole.GOVT_ADMIN,   "password": "admin123"},
        {"name": "Kavita Rao",      "mobile": "9876543241", "role": UserRole.GOVT_ADMIN,   "password": "admin123"},
        {"name": "Mohan Lal",       "mobile": "9876543242", "role": UserRole.GOVT_ADMIN,   "password": "admin123"},
        # CSC Operators
        {"name": "Aarav Joshi",     "mobile": "9876543250", "role": UserRole.CSC_OPERATOR, "password": "csc123"},
        {"name": "Nisha Tiwari",    "mobile": "9876543251", "role": UserRole.CSC_OPERATOR, "password": "csc123"},
        {"name": "Rohit Patil",     "mobile": "9876543252", "role": UserRole.CSC_OPERATOR, "password": "csc123"},
    ]
    users = []
    for u_data in demo_users:
        u = User(
            id=uuid.uuid4(),
            name=u_data["name"],
            mobile=u_data["mobile"],
            role=u_data["role"],
            password_hash=hash_password(u_data["password"]),
        )
        db.add(u)
        users.append(u)
    await db.flush()
    print(f"[OK] Inserted {len(users)} users")

    # ── 4. Farmer Profiles ──────────────────────────────────────────────────────
    farmer_profiles_data = [
        {"village": "Fatehgarh", "district": "Ludhiana", "state": "Punjab",
         "land_holding": 5.5, "bank_account_number_encrypted": "XXXX1234", "bank_ifsc_code": "PUNB0001234"},
        {"village": "Rajgarh", "district": "Amritsar", "state": "Punjab",
         "land_holding": 3.2, "bank_account_number_encrypted": "XXXX5678", "bank_ifsc_code": "SBIN0005678"},
        {"village": "Sherpur", "district": "Karnal", "state": "Haryana",
         "land_holding": 7.0, "bank_account_number_encrypted": "XXXX9012", "bank_ifsc_code": "HDFC0009012"},
    ]
    farmers = [u for u in users if u.role == UserRole.FARMER]
    for farmer, fp_data in zip(farmers, farmer_profiles_data):
        fp = FarmerProfile(id=uuid.uuid4(), user_id=farmer.id, **fp_data)
        db.add(fp)
    await db.flush()
    print("[OK] Inserted 3 farmer profiles")

    # ── 5. Slot Bookings ─────────────────────────────────────────────────────────
    today = date.today()
    bookings = []
    statuses = [
        BookingStatus.BOOKED, BookingStatus.ARRIVED, BookingStatus.IN_QUEUE,
        BookingStatus.PROCESSING, BookingStatus.COMPLETED, BookingStatus.CANCELLED,
        BookingStatus.BOOKED, BookingStatus.BOOKED, BookingStatus.COMPLETED, BookingStatus.PROCESSING,
        BookingStatus.BOOKED, BookingStatus.IN_QUEUE, BookingStatus.COMPLETED, BookingStatus.BOOKED,
        BookingStatus.COMPLETED, BookingStatus.BOOKED, BookingStatus.CANCELLED, BookingStatus.BOOKED,
        BookingStatus.PROCESSING, BookingStatus.COMPLETED,
    ]
    token_counters = {c.crop_code: 0 for c in crops}

    for i in range(20):
        farmer = random.choice(farmers)
        centre = random.choice(centres)
        crop = random.choice(crops)
        slot_date = today + timedelta(days=random.randint(-2, 5))
        slot_hour = random.randint(9, 16)
        slot_start = time(slot_hour, 0)
        slot_end = time(slot_hour + 1, 0) if slot_hour < 16 else time(16, 30)

        token_counters[crop.crop_code] += 1
        token_number = f"{crop.crop_code}-{token_counters[crop.crop_code]:05d}"

        qr_data = {
            "token": token_number,
            "farmer_id": str(farmer.id),
            "centre_id": str(centre.id),
            "slot_date": slot_date.isoformat(),
            "slot_start": slot_start.strftime("%H:%M"),
            "crop_id": str(crop.id),
        }

        booking = SlotBooking(
            id=uuid.uuid4(),
            farmer_id=farmer.id,
            centre_id=centre.id,
            crop_id=crop.id,
            slot_date=slot_date,
            slot_start_time=slot_start,
            slot_end_time=slot_end,
            token_number=token_number,
            qr_code_data=json.dumps(qr_data),
            status=statuses[i],
            declared_quantity_q=round(random.uniform(5, 100), 2),
            created_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 48)),
        )
        db.add(booking)
        bookings.append(booking)
    await db.flush()
    print(f"[OK] Inserted {len(bookings)} slot bookings")

    # ── 6. Transactions ──────────────────────────────────────────────────────────
    staff = [u for u in users if u.role == UserRole.MANDI_STAFF]
    completed_bookings = [b for b in bookings if b.status in [
        BookingStatus.PROCESSING, BookingStatus.COMPLETED
    ]][:10]

    txn_scenarios = [
        # (quality done, weighment done, confirmed, paid)
        (True, True, True, True),
        (True, True, True, False),
        (True, True, False, False),
        (True, False, False, False),
        (False, False, False, False),
        (True, True, True, True),
        (True, True, True, False),
        (True, False, False, False),
        (True, True, True, True),
        (False, False, False, False),
    ]

    for booking, (q_done, w_done, confirmed, paid) in zip(completed_bookings, txn_scenarios):
        crop = next(c for c in crops if c.id == booking.crop_id)
        gross = round(random.uniform(20, 60), 2)
        tare = round(random.uniform(1, 3), 2)
        net = round(gross - tare, 3)
        total = round(net * crop.msp_per_quintal, 2)

        txn = Transaction(
            id=uuid.uuid4(),
            slot_booking_id=booking.id,
            farmer_id=booking.farmer_id,
            centre_id=booking.centre_id,
            crop_id=booking.crop_id,
            msp_per_q=crop.msp_per_quintal,
            staff_id=random.choice(staff).id,
            gross_weight_q=gross if w_done else None,
            tare_weight_q=tare if w_done else None,
            net_weight_q=net if w_done else None,
            total_amount=total if confirmed else None,
            quality_status=QualityStatus.ACCEPTED if q_done else None,
            moisture_percent=round(random.uniform(8, 14), 1) if q_done else None,
            foreign_matter_percent=round(random.uniform(0.1, 2.0), 2) if q_done else None,
            procurement_status=ProcurementStatus.CONFIRMED if confirmed else ProcurementStatus.PENDING,
            payment_status=PaymentStatus.PAID if paid else (
                PaymentStatus.NOT_INITIATED if confirmed else PaymentStatus.NOT_INITIATED
            ),
            payment_ref=f"PFMS-{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))}" if paid else None,
            pfms_transaction_id=f"UTR{''.join(random.choices('0123456789', k=16))}" if paid else None,
            completed_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(0, 6)) if confirmed else None,
            created_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 24)),
        )
        db.add(txn)
    await db.flush()
    print("[OK] Inserted 10 transactions")

    # ── 7. Grievances ─────────────────────────────────────────────────────────────
    officers = [u for u in users if u.role == UserRole.MANDI_OFFICER]
    grievance_data = [
        (GrievanceCategory.SLOT_ISSUE, "My slot was double-booked", GrievanceStatus.OPEN),
        (GrievanceCategory.EXCESSIVE_WAIT, "Waited 4 hours beyond my slot time", GrievanceStatus.UNDER_REVIEW),
        (GrievanceCategory.QUALITY_DISPUTE, "My wheat was incorrectly graded as rejected", GrievanceStatus.RESOLVED),
        (GrievanceCategory.PAYMENT_ISSUE, "Payment not received after 10 days of confirmation", GrievanceStatus.OPEN),
        (GrievanceCategory.WEIGHMENT_DISPUTE, "Weighment showed 20% less than actual", GrievanceStatus.CLOSED),
    ]
    for i, (cat, desc, status) in enumerate(grievance_data):
        farmer = farmers[i % len(farmers)]
        g = Grievance(
            id=uuid.uuid4(),
            farmer_id=farmer.id,
            slot_booking_id=bookings[i].id if i < len(bookings) else None,
            category=cat,
            description=desc,
            status=status,
            assigned_to=officers[0].id if status != GrievanceStatus.OPEN else None,
            resolution="Issue resolved after investigation." if status == GrievanceStatus.RESOLVED else None,
            created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 10)),
            resolved_at=datetime.now(timezone.utc) - timedelta(days=1) if status == GrievanceStatus.RESOLVED else None,
        )
        db.add(g)
    await db.flush()
    print("[OK] Inserted 5 grievances")

    # ── 8. Alert Logs ─────────────────────────────────────────────────────────────
    alert_data = [
        (AlertType.DELAY, "Transaction pending quality check for >90 minutes", AlertSeverity.HIGH),
        (AlertType.CONGESTION, "Ludhiana Mandi A at 92% capacity for tomorrow", AlertSeverity.MEDIUM),
        (AlertType.ANOMALY, "Rejection rate 45% vs 7-day avg 18% at Karnal Hub", AlertSeverity.HIGH),
    ]
    for (a_type, a_msg, a_severity), centre in zip(alert_data, centres[:3]):
        a = AlertLog(
            id=uuid.uuid4(),
            centre_id=centre.id,
            type=a_type,
            message=a_msg,
            severity=a_severity,
            is_acknowledged=False,
            created_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 5)),
        )
        db.add(a)
    await db.flush()
    print("[OK] Inserted 3 alert logs")

    # ── 9. Notifications ──────────────────────────────────────────────────────────
    notif_data = [
        ("Slot Confirmed [OK]", "Your slot at Ludhiana Mandi A is confirmed for tomorrow at 10:00 AM.", NotificationChannel.APP),
        ("Queue Update", "You are now #5 in queue. Estimated wait: 25 minutes.", NotificationChannel.APP),
        ("Payment Received 💰", "₹45,650 has been credited to your account. UTR: UTR20241015XXXX", NotificationChannel.APP),
        ("Grievance Update", "Your grievance GRV-001 is now under review.", NotificationChannel.APP),
        ("SMS Confirmation", "AnnSetu: Your slot WHT-00001 confirmed at Ludhiana Mandi A on 15/01/2025 10:00", NotificationChannel.SMS),
        ("Processing Delay Alert", "Transaction pending quality check for >90 minutes at Karnal Hub.", NotificationChannel.APP),
        ("Slot Booked via IVR", "Slot booked successfully via IVR. Token: RIC-00003", NotificationChannel.IVR),
        ("Quality Accepted", "Your wheat lot has been accepted. Quality: Good", NotificationChannel.APP),
        ("Congestion Alert", "High footfall expected tomorrow at Amritsar Centre.", NotificationChannel.APP),
        ("Registration Complete", "Welcome to AnnSetu! Your profile is complete.", NotificationChannel.APP),
    ]
    all_notif_users = farmers + staff[:2] + officers[:2]
    for i, (title, body, channel) in enumerate(notif_data):
        user = all_notif_users[i % len(all_notif_users)]
        n = Notification(
            id=uuid.uuid4(),
            user_id=user.id,
            title=title,
            body=body,
            channel=channel,
            is_read=i % 3 == 0,
            created_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 72)),
        )
        db.add(n)
    await db.flush()
    print("[OK] Inserted 10 notifications")

    await db.commit()

    # ── Print Demo Credentials ──────────────────────────────────────────────────
    print("\n" + "="*60)
    print("   ANNSETU — DEMO CREDENTIALS")
    print("="*60)
    roles = {
        "FARMER": ("farmer123", "9876543210 / 9876543211 / 9876543212"),
        "MANDI_STAFF": ("staff123", "9876543220 / 9876543221 / 9876543222"),
        "MANDI_OFFICER": ("officer123", "9876543230 / 9876543231 / 9876543232"),
        "GOVT_ADMIN": ("admin123", "9876543240 / 9876543241 / 9876543242"),
        "CSC_OPERATOR": ("csc123", "9876543250 / 9876543251 / 9876543252"),
    }
    for role, (pw, mobiles) in roles.items():
        print(f"\n  Role: {role}")
        print(f"  Mobiles: {mobiles}")
        print(f"  Password: {pw}")
    print("\n" + "="*60)

    if close_db:
        await db.close()


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[OK] Tables created (if not exist)")


async def initialize_demo_data():
    """Create the schema and seed demo data once, safely across restarts."""
    await create_tables()
    async with AsyncSessionLocal() as db:
        existing_user = await db.scalar(select(User).limit(1))
        if existing_user:
            print("[OK] Demo data already exists; skipping seed.")
            return
        await run_seed(db)


if __name__ == "__main__":
    async def main():
        await initialize_demo_data()
    asyncio.run(main())
