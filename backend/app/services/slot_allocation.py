"""Smart Slot Allocation Service."""
import uuid
import json
from datetime import date, time, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.slot_booking import SlotBooking, BookingStatus
from app.models.procurement_centre import ProcurementCentre
from app.models.crop import Crop
from app.models.user import User
from app.models.notification import Notification, NotificationChannel
from app.utils.qr_generator import generate_qr_base64


class SlotAllocationService:
    """
    Allocates the optimal time slot for a farmer's crop booking.
    Divides 9AM-5PM into slots of avg_processing_time_minutes.
    Finds first available slot on preferred_date or within next 7 days.
    """

    OPERATING_START = time(9, 0)
    OPERATING_END = time(17, 0)

    async def allocate(
        self,
        farmer_id: uuid.UUID,
        centre_id: uuid.UUID,
        crop_id: uuid.UUID,
        preferred_date: date,
        declared_qty: float,
        preferred_slot_start_time: time | None,
        db: AsyncSession,
    ) -> SlotBooking:
        # Fetch centre and crop
        centre_result = await db.execute(
            select(ProcurementCentre).where(ProcurementCentre.id == centre_id)
        )
        centre = centre_result.scalar_one_or_none()
        if not centre:
            raise ValueError("Procurement centre not found")

        crop_result = await db.execute(select(Crop).where(Crop.id == crop_id))
        crop = crop_result.scalar_one_or_none()
        if not crop:
            raise ValueError("Crop not found")

        # Build time slots for the operating window
        slots = self._build_slots(centre.avg_processing_time_minutes)
        total_slots = len(slots)
        if total_slots == 0:
            raise ValueError("No valid slots can be computed for this centre")

        per_slot_capacity = max(1, centre.daily_capacity // total_slots)

        # Search preferred_date + next 7 days
        allocated_date = None
        allocated_slot = None
        for day_offset in range(8):
            candidate_date = preferred_date + timedelta(days=day_offset)
            slot_counts = await self._count_bookings_per_slot(
                db, centre_id, candidate_date, slots
            )
            candidate_slots = slots
            if day_offset == 0 and preferred_slot_start_time:
                candidate_slots = [slot for slot in slots if slot[0] == preferred_slot_start_time]
                if not candidate_slots:
                    raise ValueError("Selected time slot is not available at this centre")
            for slot_start, slot_end in candidate_slots:
                key = f"{slot_start.strftime('%H:%M')}-{slot_end.strftime('%H:%M')}"
                if slot_counts.get(key, 0) < per_slot_capacity:
                    allocated_date = candidate_date
                    allocated_slot = (slot_start, slot_end)
                    break
            if allocated_slot:
                break

        if not allocated_slot or not allocated_date:
            raise ValueError("No available slots in the next 7 days")

        # Generate sequential token number
        token_num = await self._next_token_seq(db, crop.crop_code)
        token_number = f"{crop.crop_code}-{token_num:05d}"

        # Build QR data
        qr_data = {
            "token": token_number,
            "farmer_id": str(farmer_id),
            "centre_id": str(centre_id),
            "slot_date": allocated_date.isoformat(),
            "slot_start": allocated_slot[0].strftime("%H:%M"),
            "crop_id": str(crop_id),
        }
        qr_base64 = generate_qr_base64(qr_data)

        booking = SlotBooking(
            id=uuid.uuid4(),
            farmer_id=farmer_id,
            centre_id=centre_id,
            crop_id=crop_id,
            slot_date=allocated_date,
            slot_start_time=allocated_slot[0],
            slot_end_time=allocated_slot[1],
            token_number=token_number,
            qr_code_data=json.dumps(qr_data),
            status=BookingStatus.BOOKED,
            declared_quantity_q=declared_qty,
        )
        db.add(booking)
        await db.flush()

        # Send confirmation notification
        farmer_result = await db.execute(select(User).where(User.id == farmer_id))
        farmer = farmer_result.scalar_one_or_none()
        if farmer:
            notif = Notification(
                id=uuid.uuid4(),
                user_id=farmer_id,
                title="Slot Booking Confirmed ✓",
                body=(
                    f"Your slot at {centre.name} is confirmed for "
                    f"{allocated_date.strftime('%d %b %Y')} "
                    f"{allocated_slot[0].strftime('%I:%M %p')} – {allocated_slot[1].strftime('%I:%M %p')}. "
                    f"Token: {token_number}"
                ),
                channel=NotificationChannel.APP,
            )
            db.add(notif)
            # Simulate SMS log
            print(
                f"[SMS] To: +91{farmer.mobile} | "
                f"AnnSetu: Slot confirmed at {centre.name} on "
                f"{allocated_date.strftime('%d/%m/%Y')} {allocated_slot[0].strftime('%H:%M')}. "
                f"Token: {token_number}"
            )

        # Attach base64 QR for the response (stored on the returned object, not in DB)
        booking.qr_code_data = json.dumps({**qr_data, "_qr_base64": qr_base64})
        return booking

    def _build_slots(self, avg_minutes: int) -> list[tuple[time, time]]:
        """Divide 9AM-5PM into slots of avg_minutes each."""
        slots = []
        start_hour, end_hour = 9, 17
        current_minutes = start_hour * 60
        end_minutes = end_hour * 60

        while current_minutes + avg_minutes <= end_minutes:
            s = time(current_minutes // 60, current_minutes % 60)
            e_minutes = current_minutes + avg_minutes
            e = time(e_minutes // 60, e_minutes % 60)
            slots.append((s, e))
            current_minutes = e_minutes

        return slots

    async def _count_bookings_per_slot(
        self,
        db: AsyncSession,
        centre_id: uuid.UUID,
        target_date: date,
        slots: list[tuple[time, time]],
    ) -> dict[str, int]:
        result = await db.execute(
            select(SlotBooking).where(
                SlotBooking.centre_id == centre_id,
                SlotBooking.slot_date == target_date,
                SlotBooking.status != BookingStatus.CANCELLED,
            )
        )
        bookings = result.scalars().all()
        counts: dict[str, int] = {}
        for b in bookings:
            key = f"{b.slot_start_time.strftime('%H:%M')}-{b.slot_end_time.strftime('%H:%M')}"
            counts[key] = counts.get(key, 0) + 1
        return counts

    async def _next_token_seq(self, db: AsyncSession, crop_code: str) -> int:
        """Get next sequential number for this crop code."""
        result = await db.execute(
            select(func.count()).where(
                SlotBooking.token_number.like(f"{crop_code}-%")
            )
        )
        count = result.scalar() or 0
        return count + 1
