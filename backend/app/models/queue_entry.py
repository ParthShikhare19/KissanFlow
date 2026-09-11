"""SQLAlchemy ORM model for QueueEntry."""
import uuid
import enum
from datetime import datetime
from sqlalchemy import Integer, DateTime, ForeignKey, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class QueueStatus(str, enum.Enum):
    WAITING = "WAITING"
    CALLED = "CALLED"
    PROCESSING = "PROCESSING"
    DONE = "DONE"


class QueueEntry(Base):
    __tablename__ = "queue_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slot_booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("slot_bookings.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    centre_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("procurement_centres.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_wait_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[QueueStatus] = mapped_column(
        SAEnum(QueueStatus), nullable=False, default=QueueStatus.WAITING
    )
    gate_entry_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    slot_booking: Mapped["SlotBooking"] = relationship("SlotBooking", back_populates="queue_entry")
    centre: Mapped["ProcurementCentre"] = relationship("ProcurementCentre", back_populates="queue_entries")
