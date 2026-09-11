"""
KissanFlow — Database Seed Script
Run: python seed.py

Inserts demo data in correct FK order.
Prints all credentials at the end.

Data is fully deterministic (#17): every value is derived from loop indices,
so two fresh installations produce identical demo results.
All sections are idempotent (#3): re-running never duplicates rows.
"""
import asyncio
import uuid
import json
from datetime import date, time, datetime, timezone, timedelta

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from dotenv import load_dotenv
load_dotenv()

from app.database import AsyncSessionLocal, engine
from app.database import Base
from app.models import *
from app.utils.security import hash_password
from app.utils.qr_generator import generate_qr_base64


# Deterministic status plan for the 20 base bookings (per loop index).
BASE_BOOKING_STATUSES = [
    BookingStatus.BOOKED, BookingStatus.ARRIVED, BookingStatus.IN_QUEUE,
    BookingStatus.PROCESSING, BookingStatus.COMPLETED, BookingStatus.CANCELLED,
    BookingStatus.BOOKED, BookingStatus.BOOKED, BookingStatus.COMPLETED, BookingStatus.PROCESSING,
    BookingStatus.BOOKED, BookingStatus.IN_QUEUE, BookingStatus.COMPLETED, BookingStatus.BOOKED,
    BookingStatus.COMPLETED, BookingStatus.BOOKED, BookingStatus.CANCELLED, BookingStatus.BOOKED,
    BookingStatus.PROCESSING, BookingStatus.COMPLETED,
]
# Deterministic slot-date offsets (days from today) for the 20 base bookings.
BASE_BOOKING_DAY_OFFSETS = [-2, -2, -1, 0, 0, 0, 0, 1, -1, 0, 1, 0, -1, 2, -1, 1, -2, 3, 0, -1]


async def add_missing_columns():
    """Upgrade pre-existing databases in place with the new columns.

    Safe on fresh databases: tables that don't exist yet are skipped here and
    created with the current schema by create_tables().
    """
    from sqlalchemy import inspect as sa_inspect

    is_pg = engine.dialect.name == "postgresql"

    def _migrate_sync(sync_conn):
        insp = sa_inspect(sync_conn)
        if insp.has_table("users"):
            existing = {c["name"] for c in insp.get_columns("users")}
            if "assigned_centre_id" not in existing:
                ddl = "UUID NULL" if is_pg else "CHAR(32)"
                sync_conn.execute(text(f"ALTER TABLE users ADD COLUMN assigned_centre_id {ddl}"))
        if insp.has_table("transactions"):
            existing = {c["name"] for c in insp.get_columns("transactions")}
            for col in ("quality_done_at", "weighment_done_at", "confirmed_at",
                        "payment_initiated_at", "paid_at"):
                if col not in existing:
                    ddl = "TIMESTAMPTZ NULL" if is_pg else "DATETIME"
                    sync_conn.execute(text(f"ALTER TABLE transactions ADD COLUMN {col} {ddl}"))

    async with engine.begin() as conn:
        await conn.run_sync(_migrate_sync)
    print("[OK] Schema columns up to date")


async def run_seed(db: AsyncSession):
    """Seed all demo data. Idempotent: every section skips if rows exist."""
    # ── 1. Procurement Centres ────────────────────────────────────────────────
    existing_centres = (await db.scalars(select(ProcurementCentre))).all()
    if existing_centres:
        centres = existing_centres
        print(f"[SKIP] {len(centres)} procurement centres already exist")
    else:
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
    existing_crops = (await db.scalars(select(Crop))).all()
    if existing_crops:
        crops = existing_crops
        print(f"[SKIP] {len(crops)} crops already exist")
    else:
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
    existing_users = (await db.scalars(select(User))).all()
    if existing_users:
        users = existing_users
        print(f"[SKIP] {len(users)} users already exist")
    else:
        # 3 farmers, 3 staff, 3 officers, 3 govt admins, 3 CSC operators = 15 users.
        # Staff/officer i is assigned to centre i (#10) so queue and transaction
        # authorisation has real data to enforce.
        demo_users = [
            # Farmers
            {"name": "Ranjit Singh",    "mobile": "9876543210", "role": UserRole.FARMER,       "password": "farmer123"},
            {"name": "Meera Devi",      "mobile": "9876543211", "role": UserRole.FARMER,       "password": "farmer123"},
            {"name": "Suresh Kumar",    "mobile": "9876543212", "role": UserRole.FARMER,       "password": "farmer123"},
            # Mandi Staff
            {"name": "Amit Sharma",     "mobile": "9876543220", "role": UserRole.MANDI_STAFF,  "password": "staff123", "centre": 0},
            {"name": "Priya Verma",     "mobile": "9876543221", "role": UserRole.MANDI_STAFF,  "password": "staff123", "centre": 1},
            {"name": "Deepak Yadav",    "mobile": "9876543222", "role": UserRole.MANDI_STAFF,  "password": "staff123", "centre": 2},
            # Mandi Officers
            {"name": "Rajesh Gupta",    "mobile": "9876543230", "role": UserRole.MANDI_OFFICER,"password": "officer123", "centre": 0},
            {"name": "Sunita Pandey",   "mobile": "9876543231", "role": UserRole.MANDI_OFFICER,"password": "officer123", "centre": 1},
            {"name": "Vivek Mishra",    "mobile": "9876543232", "role": UserRole.MANDI_OFFICER,"password": "officer123", "centre": 2},
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
                assigned_centre_id=centres[u_data["centre"]].id if "centre" in u_data else None,
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
    existing_profiles = (await db.scalars(select(FarmerProfile))).all()
    if existing_profiles:
        print(f"[SKIP] {len(existing_profiles)} farmer profiles already exist")
    else:
        for farmer, fp_data in zip(farmers, farmer_profiles_data):
            fp = FarmerProfile(id=uuid.uuid4(), user_id=farmer.id, **fp_data)
            db.add(fp)
        await db.flush()
        print("[OK] Inserted 3 farmer profiles")

    # ── 5. Slot Bookings ─────────────────────────────────────────────────────────
    existing_bookings = (await db.scalars(select(SlotBooking))).all()
    if existing_bookings:
        bookings = existing_bookings
        print(f"[SKIP] {len(bookings)} slot bookings already exist")
    else:
        today = date.today()
        now = datetime.now(timezone.utc)
        bookings = []
        token_counters: dict[str, int] = {}
        for i in range(20):
            # Deterministic assignment from the loop index (#17).
            farmer = farmers[i % len(farmers)]
            centre = centres[i % len(centres)]
            crop = crops[i % len(crops)]
            slot_date = today + timedelta(days=BASE_BOOKING_DAY_OFFSETS[i])
            slot_hour = 9 + (i % 8)
            slot_start = time(slot_hour, 0)
            slot_end = time(slot_hour + 1, 0) if slot_hour < 16 else time(16, 30)

            token_counters[crop.crop_code] = token_counters.get(crop.crop_code, 0) + 1
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
                status=BASE_BOOKING_STATUSES[i],
                declared_quantity_q=round(15 + (i * 7) % 80 + 0.5, 2),
                created_at=now - timedelta(hours=6 + i * 2),
            )
            db.add(booking)
            bookings.append(booking)
        await db.flush()
        print(f"[OK] Inserted {len(bookings)} slot bookings")

    # ── 6. Transactions ──────────────────────────────────────────────────────────
    existing_txns = (await db.scalars(select(Transaction))).all()
    if existing_txns:
        print(f"[SKIP] {len(existing_txns)} transactions already exist")
    else:
        staff = [u for u in users if u.role == UserRole.MANDI_STAFF]
        completed_bookings = [b for b in bookings if b.status in [
            BookingStatus.PROCESSING, BookingStatus.COMPLETED
        ]][:10]
        now = datetime.now(timezone.utc)

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

        for idx, (booking, (q_done, w_done, confirmed, paid)) in enumerate(
            zip(completed_bookings, txn_scenarios)
        ):
            crop = next(c for c in crops if c.id == booking.crop_id)
            gross = round(25 + (idx * 3) % 30, 2)
            tare = round(1.0 + (idx % 3) * 0.5, 2)
            net = round(gross - tare, 3)
            total = round(net * crop.msp_per_quintal, 2)

            txn = Transaction(
                id=uuid.uuid4(),
                slot_booking_id=booking.id,
                farmer_id=booking.farmer_id,
                centre_id=booking.centre_id,
                crop_id=booking.crop_id,
                msp_per_q=crop.msp_per_quintal,
                staff_id=staff[idx % len(staff)].id,
                gross_weight_q=gross if w_done else None,
                tare_weight_q=tare if w_done else None,
                net_weight_q=net if w_done else None,
                total_amount=total if confirmed else None,
                quality_status=QualityStatus.ACCEPTED if q_done else None,
                moisture_percent=round(8.0 + idx * 0.6, 1) if q_done else None,
                foreign_matter_percent=round(0.2 + (idx % 6) * 0.3, 2) if q_done else None,
                procurement_status=ProcurementStatus.CONFIRMED if confirmed else ProcurementStatus.PENDING,
                payment_status=PaymentStatus.PAID if paid else PaymentStatus.NOT_INITIATED,
                payment_ref=f"PFMS-DEMO-{idx + 1:04d}" if paid else None,
                pfms_transaction_id=f"UTR{(idx + 1) * 1000000007:016d}" if paid else None,
                completed_at=now - timedelta(hours=1 + idx) if confirmed else None,
                created_at=now - timedelta(hours=2 + idx),
                quality_done_at=now - timedelta(hours=2 + idx, minutes=-30) if q_done else None,
                weighment_done_at=now - timedelta(hours=2 + idx, minutes=-50) if w_done else None,
                confirmed_at=now - timedelta(hours=1 + idx, minutes=-40) if confirmed else None,
                payment_initiated_at=now - timedelta(hours=1 + idx, minutes=-20) if paid else None,
                paid_at=now - timedelta(hours=1 + idx) if paid else None,
            )
            db.add(txn)
        await db.flush()
        print(f"[OK] Inserted 10 transactions")

    # ── 7. Grievances ─────────────────────────────────────────────────────────────
    existing_grievances = (await db.scalars(select(Grievance))).all()
    if existing_grievances:
        print(f"[SKIP] {len(existing_grievances)} grievances already exist")
    else:
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
                created_at=datetime.now(timezone.utc) - timedelta(days=i + 1),
                resolved_at=datetime.now(timezone.utc) - timedelta(days=1) if status == GrievanceStatus.RESOLVED else None,
            )
            db.add(g)
        await db.flush()
        print("[OK] Inserted 5 grievances")

    # ── 8. Alert Logs ─────────────────────────────────────────────────────────────
    existing_alerts = (await db.scalars(select(AlertLog))).all()
    if existing_alerts:
        print(f"[SKIP] {len(existing_alerts)} alert logs already exist")
    else:
        alert_data = [
            (AlertType.DELAY, "Transaction pending quality check for >90 minutes", AlertSeverity.HIGH),
            (AlertType.CONGESTION, "Ludhiana Mandi A at 92% capacity for tomorrow", AlertSeverity.MEDIUM),
            (AlertType.ANOMALY, "Rejection rate 45% vs 7-day avg 18% at Karnal Hub", AlertSeverity.HIGH),
        ]
        for i, ((a_type, a_msg, a_severity), centre) in enumerate(zip(alert_data, centres[:3])):
            a = AlertLog(
                id=uuid.uuid4(),
                centre_id=centre.id,
                type=a_type,
                message=a_msg,
                severity=a_severity,
                is_acknowledged=False,
                created_at=datetime.now(timezone.utc) - timedelta(hours=i + 1),
            )
            db.add(a)
        await db.flush()
        print("[OK] Inserted 3 alert logs")

    # ── 9. Notifications ──────────────────────────────────────────────────────────
    existing_notifs = (await db.scalars(select(Notification))).all()
    if existing_notifs:
        print(f"[SKIP] {len(existing_notifs)} notifications already exist")
    else:
        notif_data = [
            ("Slot Confirmed [OK]", "Your slot at Ludhiana Mandi A is confirmed for tomorrow at 10:00 AM.", NotificationChannel.APP),
            ("Queue Update", "You are now #5 in queue. Estimated wait: 25 minutes.", NotificationChannel.APP),
            ("Payment Received 💰", "₹45,650 has been credited to your account. UTR: UTR20241015XXXX", NotificationChannel.APP),
            ("Grievance Update", "Your grievance GRV-001 is now under review.", NotificationChannel.APP),
            ("SMS Confirmation", "KissanFlow: Your slot WHT-00001 confirmed at Ludhiana Mandi A on 15/01/2025 10:00", NotificationChannel.SMS),
            ("Processing Delay Alert", "Transaction pending quality check for >90 minutes at Karnal Hub.", NotificationChannel.APP),
            ("Slot Booked via IVR", "Slot booked successfully via IVR. Token: RIC-00003", NotificationChannel.IVR),
            ("Quality Accepted", "Your wheat lot has been accepted. Quality: Good", NotificationChannel.APP),
            ("Congestion Alert", "High footfall expected tomorrow at Amritsar Centre.", NotificationChannel.APP),
            ("Registration Complete", "Welcome to KissanFlow! Your profile is complete.", NotificationChannel.APP),
        ]
        all_notif_users = farmers + [u for u in users if u.role == UserRole.MANDI_STAFF][:2] + [
            u for u in users if u.role == UserRole.MANDI_OFFICER
        ][:2]
        for i, (title, body, channel) in enumerate(notif_data):
            user = all_notif_users[i % len(all_notif_users)]
            n = Notification(
                id=uuid.uuid4(),
                user_id=user.id,
                title=title,
                body=body,
                channel=channel,
                is_read=i % 3 == 0,
                created_at=datetime.now(timezone.utc) - timedelta(hours=i + 1),
            )
            db.add(n)
        await db.flush()
        print("[OK] Inserted 10 notifications")

    if db.in_transaction():
        await db.commit()

    # ── Print Demo Credentials ──────────────────────────────────────────────────
    print("\n" + "="*60)
    print("   KISSANFLOW — DEMO CREDENTIALS")
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


async def ensure_demo_bookings(db):
    """Add stable bookings for completed, ongoing, and future-flow testing."""
    demo_tokens = {"DEMO-COMP-001", "DEMO-QUEUE-001", "DEMO-FUTR-001"}
    existing = await db.scalars(
        select(SlotBooking).where(SlotBooking.token_number.in_(demo_tokens))
    )
    if existing.first():
        print("[OK] Demo booking scenarios already exist; skipping.")
        return

    farmers = {
        mobile: await db.scalar(select(User).where(User.mobile == mobile))
        for mobile in ("9876543210", "9876543211", "9876543212")
    }
    centre = await db.scalar(
        select(ProcurementCentre).where(ProcurementCentre.name == "Ludhiana Mandi A")
    )
    crops = {
        name: await db.scalar(select(Crop).where(Crop.name == name))
        for name in ("Wheat", "Rice", "Mustard")
    }
    if not centre or any(value is None for value in farmers.values()) or any(
        value is None for value in crops.values()
    ):
        print("[WARN] Demo booking scenarios skipped: base seed data is incomplete.")
        return

    today = date.today()
    now = datetime.now(timezone.utc)
    scenarios = [
        (
            "DEMO-COMP-001", farmers["9876543210"], crops["Wheat"],
            today - timedelta(days=1), time(10, 0), BookingStatus.COMPLETED,
        ),
        (
            "DEMO-QUEUE-001", farmers["9876543211"], crops["Rice"],
            today, time(11, 0), BookingStatus.IN_QUEUE,
        ),
        (
            "DEMO-FUTR-001", farmers["9876543212"], crops["Mustard"],
            today + timedelta(days=2), time(9, 0), BookingStatus.BOOKED,
        ),
    ]
    created = {}
    for token, farmer, crop, slot_date, slot_start, status in scenarios:
        qr_data = {
            "token": token,
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
            slot_end_time=time(slot_start.hour + 1, slot_start.minute),
            token_number=token,
            qr_code_data=json.dumps(qr_data),
            status=status,
            declared_quantity_q=25.0,
            created_at=now - timedelta(days=1 if status == BookingStatus.COMPLETED else 0),
        )
        db.add(booking)
        created[token] = booking
    await db.flush()

    completed = created["DEMO-COMP-001"]
    db.add(Transaction(
        id=uuid.uuid4(),
        slot_booking_id=completed.id,
        farmer_id=completed.farmer_id,
        centre_id=completed.centre_id,
        crop_id=completed.crop_id,
        gross_weight_q=26.0,
        tare_weight_q=1.0,
        net_weight_q=25.0,
        msp_per_q=crops["Wheat"].msp_per_quintal,
        total_amount=25.0 * crops["Wheat"].msp_per_quintal,
        quality_status=QualityStatus.ACCEPTED,
        procurement_status=ProcurementStatus.CONFIRMED,
        payment_status=PaymentStatus.PAID,
        payment_ref="PFMS-DEMO-001",
        pfms_transaction_id="UTR-DEMO-001",
        completed_at=now - timedelta(hours=4),
        created_at=now - timedelta(days=1),
        paid_at=now - timedelta(hours=4),
    ))

    ongoing = created["DEMO-QUEUE-001"]
    db.add(Transaction(
        id=uuid.uuid4(),
        slot_booking_id=ongoing.id,
        farmer_id=ongoing.farmer_id,
        centre_id=ongoing.centre_id,
        crop_id=ongoing.crop_id,
        msp_per_q=crops["Rice"].msp_per_quintal,
        quality_status=QualityStatus.ACCEPTED,
        procurement_status=ProcurementStatus.PENDING,
        payment_status=PaymentStatus.NOT_INITIATED,
        created_at=now,
    ))
    db.add(QueueEntry(
        id=uuid.uuid4(),
        slot_booking_id=ongoing.id,
        centre_id=ongoing.centre_id,
        position=1,
        estimated_wait_minutes=20,
        status=QueueStatus.WAITING,
        gate_entry_time=now - timedelta(minutes=12),
    ))
    await db.flush()
    print("[OK] Added demo bookings: completed, ongoing queue, and future slot")


async def ensure_busy_demo_data(db):
    """Add a deterministic busy-day workload for dashboards and process timing."""
    existing_load = await db.scalar(
        select(SlotBooking.id).where(SlotBooking.token_number.like("LOAD-%")).limit(1)
    )
    if existing_load:
        print("[OK] Busy demo workload already exists; skipping.")
        return

    farmers = list((await db.scalars(select(User).where(User.role == UserRole.FARMER))).all())
    staff = list((await db.scalars(select(User).where(User.role == UserRole.MANDI_STAFF))).all())
    centres = list((await db.scalars(select(ProcurementCentre))).all())
    crops = list((await db.scalars(select(Crop))).all())
    if not farmers or not staff or not centres or not crops:
        print("[WARN] Busy demo workload skipped: base seed data is incomplete.")
        return

    today = date.today()
    now = datetime.now(timezone.utc)
    created_bookings = []
    for index in range(60):
        day_offset = (index % 15) - 7
        slot_date = today + timedelta(days=day_offset)
        slot_start = time(9 + (index % 8), 0 if index % 2 == 0 else 30)
        if slot_start >= time(17, 0):
            slot_start = time(16, 0)
        slot_end = time(slot_start.hour + 1, slot_start.minute)
        if slot_end > time(17, 0):
            slot_end = time(17, 0)

        if day_offset < 0:
            status = BookingStatus.CANCELLED if index % 13 == 0 else BookingStatus.COMPLETED
        elif day_offset == 0:
            status = [BookingStatus.BOOKED, BookingStatus.IN_QUEUE, BookingStatus.PROCESSING][(index // 15) % 3]
        else:
            status = BookingStatus.BOOKED

        farmer = farmers[index % len(farmers)]
        centre = centres[index % len(centres)]
        crop = crops[index % len(crops)]
        created_at = now - timedelta(days=max(0, -day_offset), hours=4 + index % 5)
        token = f"LOAD-{index + 1:04d}"
        qr_data = {
            "token": token,
            "farmer_id": str(farmer.id),
            "centre_id": str(centre.id),
            "slot_date": slot_date.isoformat(),
            "slot_start": slot_start.strftime("%H:%M"),
            "crop_id": str(crop.id),
        }
        booking = SlotBooking(
            id=uuid.uuid4(), farmer_id=farmer.id, centre_id=centre.id, crop_id=crop.id,
            slot_date=slot_date, slot_start_time=slot_start, slot_end_time=slot_end,
            token_number=token, qr_code_data=json.dumps(qr_data), status=status,
            declared_quantity_q=round(12 + (index * 7) % 70, 2), created_at=created_at,
        )
        db.add(booking)
        created_bookings.append((booking, farmer, centre, crop, index))
    await db.flush()

    for booking, farmer, centre, crop, index in created_bookings:
        if booking.status not in [BookingStatus.COMPLETED, BookingStatus.IN_QUEUE, BookingStatus.PROCESSING]:
            continue
        gate_entry = booking.created_at + timedelta(minutes=35 + index % 35)
        queue_status = QueueStatus.DONE if booking.status == BookingStatus.COMPLETED else (
            QueueStatus.PROCESSING if booking.status == BookingStatus.PROCESSING else QueueStatus.WAITING
        )
        db.add(QueueEntry(
            id=uuid.uuid4(), slot_booking_id=booking.id, centre_id=centre.id,
            position=(index % 12) + 1, estimated_wait_minutes=20 + (index % 5) * 5,
            status=queue_status, gate_entry_time=gate_entry,
        ))

        processing_started = gate_entry + timedelta(minutes=18 + index % 25)
        is_completed = booking.status == BookingStatus.COMPLETED
        completed_at = processing_started + timedelta(minutes=55 + index % 70) if is_completed else None
        net_weight = round(20 + (index % 30), 3)
        db.add(Transaction(
            id=uuid.uuid4(), slot_booking_id=booking.id, farmer_id=farmer.id,
            centre_id=centre.id, crop_id=crop.id, staff_id=staff[index % len(staff)].id,
            gross_weight_q=net_weight + 1.5 if is_completed else None,
            tare_weight_q=1.5 if is_completed else None,
            net_weight_q=net_weight if is_completed else None,
            msp_per_q=crop.msp_per_quintal,
            total_amount=round(net_weight * crop.msp_per_quintal, 2) if is_completed else None,
            quality_status=QualityStatus.ACCEPTED if is_completed else None,
            moisture_percent=round(9 + (index % 40) / 10, 1) if is_completed else None,
            foreign_matter_percent=round(0.3 + (index % 10) / 10, 1) if is_completed else None,
            procurement_status=ProcurementStatus.CONFIRMED if is_completed else ProcurementStatus.PENDING,
            payment_status=PaymentStatus.PAID if is_completed and index % 4 != 0 else PaymentStatus.NOT_INITIATED,
            payment_ref=f"PFMS-LOAD-{index + 1:04d}" if is_completed and index % 4 != 0 else None,
            pfms_transaction_id=f"UTR-LOAD-{index + 1:04d}" if is_completed and index % 4 != 0 else None,
            completed_at=completed_at, created_at=processing_started,
            paid_at=completed_at if is_completed and index % 4 != 0 else None,
        ))
    await db.flush()
    print("[OK] Added 60 busy demo bookings with queue and process timing data")


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[OK] Tables created (if not exist)")


async def initialize_demo_data():
    """Create the schema and seed demo data once, safely across restarts."""
    await create_tables()
    await add_missing_columns()
    async with AsyncSessionLocal() as db:
        existing_user = await db.scalar(select(User).limit(1))
        if existing_user:
            await ensure_demo_bookings(db)
            await ensure_busy_demo_data(db)
            await db.commit()
            return
        await run_seed(db)
        await ensure_demo_bookings(db)
        await ensure_busy_demo_data(db)
        await db.commit()


if __name__ == "__main__":
    async def main():
        await initialize_demo_data()
    asyncio.run(main())
