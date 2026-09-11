"""SQLAlchemy ORM model for Grievance."""
import uuid
import enum
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid
from app.database import Base


class GrievanceCategory(str, enum.Enum):
    SLOT_ISSUE = "SLOT_ISSUE"
    EXCESSIVE_WAIT = "EXCESSIVE_WAIT"
    QUALITY_DISPUTE = "QUALITY_DISPUTE"
    WEIGHMENT_DISPUTE = "WEIGHMENT_DISPUTE"
    PAYMENT_ISSUE = "PAYMENT_ISSUE"
    OTHER = "OTHER"


class GrievanceStatus(str, enum.Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class Grievance(Base):
    __tablename__ = "grievances"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slot_booking_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("slot_bookings.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[GrievanceCategory] = mapped_column(SAEnum(GrievanceCategory), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[GrievanceStatus] = mapped_column(
        SAEnum(GrievanceStatus), nullable=False, default=GrievanceStatus.OPEN
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    farmer: Mapped["User"] = relationship("User", back_populates="grievances", foreign_keys=[farmer_id])
    slot_booking: Mapped["SlotBooking | None"] = relationship("SlotBooking", back_populates="grievances")
    assigned_officer: Mapped["User | None"] = relationship(
        "User", back_populates="assigned_grievances", foreign_keys=[assigned_to]
    )
