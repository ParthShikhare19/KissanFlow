"""SQLAlchemy ORM model for Transaction."""
import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, Enum as SAEnum, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class QualityStatus(str, enum.Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CONDITIONAL = "CONDITIONAL"


class ProcurementStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, enum.Enum):
    NOT_INITIATED = "NOT_INITIATED"
    INITIATED = "INITIATED"
    PROCESSING = "PROCESSING"
    PAID = "PAID"
    FAILED = "FAILED"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slot_booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("slot_bookings.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    centre_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("procurement_centres.id"), nullable=False
    )
    crop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crops.id"), nullable=False
    )
    gross_weight_q: Mapped[float | None] = mapped_column(Float, nullable=True)
    tare_weight_q: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_weight_q: Mapped[float | None] = mapped_column(Float, nullable=True)
    msp_per_q: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_status: Mapped[QualityStatus | None] = mapped_column(SAEnum(QualityStatus), nullable=True)
    moisture_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    foreign_matter_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_photo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    weighment_photo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    procurement_status: Mapped[ProcurementStatus] = mapped_column(
        SAEnum(ProcurementStatus), nullable=False, default=ProcurementStatus.PENDING
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus), nullable=False, default=PaymentStatus.NOT_INITIATED
    )
    payment_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pfms_transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    slot_booking: Mapped["SlotBooking"] = relationship("SlotBooking", back_populates="transaction")
    farmer: Mapped["User"] = relationship("User", back_populates="transactions", foreign_keys=[farmer_id])
    centre: Mapped["ProcurementCentre"] = relationship("ProcurementCentre", back_populates="transactions")
    crop: Mapped["Crop"] = relationship("Crop", back_populates="transactions")
    staff: Mapped["User | None"] = relationship("User", foreign_keys=[staff_id])
