"""SQLAlchemy ORM model for SlotBooking."""
import uuid
import enum
import json
from datetime import datetime, date, time
from sqlalchemy import String, DateTime, Date, Time, ForeignKey, Enum as SAEnum, Float, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class BookingStatus(str, enum.Enum):
    BOOKED = "BOOKED"
    ARRIVED = "ARRIVED"
    IN_QUEUE = "IN_QUEUE"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"


class SlotBooking(Base):
    __tablename__ = "slot_bookings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    centre_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("procurement_centres.id", ondelete="CASCADE"), nullable=False, index=True
    )
    crop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crops.id"), nullable=False
    )
    slot_date: Mapped[date] = mapped_column(Date, nullable=False)
    slot_start_time: Mapped[time] = mapped_column(Time, nullable=False)
    slot_end_time: Mapped[time] = mapped_column(Time, nullable=False)
    token_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    qr_code_data: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[BookingStatus] = mapped_column(
        SAEnum(BookingStatus), nullable=False, default=BookingStatus.BOOKED
    )
    declared_quantity_q: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    farmer: Mapped["User"] = relationship("User", back_populates="slot_bookings", foreign_keys=[farmer_id])
    centre: Mapped["ProcurementCentre"] = relationship("ProcurementCentre", back_populates="slot_bookings")
    crop: Mapped["Crop"] = relationship("Crop", back_populates="slot_bookings")
    queue_entry: Mapped["QueueEntry | None"] = relationship(
        "QueueEntry", back_populates="slot_booking", uselist=False, cascade="all, delete-orphan"
    )
    transaction: Mapped["Transaction | None"] = relationship(
        "Transaction", back_populates="slot_booking", uselist=False, cascade="all, delete-orphan"
    )
    grievances: Mapped[list["Grievance"]] = relationship(
        "Grievance", back_populates="slot_booking"
    )
