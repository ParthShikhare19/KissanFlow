"""SQLAlchemy ORM model for ProcurementCentre (Mandi)."""
import uuid
from sqlalchemy import String, Float, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid
from app.database import Base


class ProcurementCentre(Base):
    __tablename__ = "procurement_centres"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    district: Mapped[str] = mapped_column(String(200), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    longitude: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    daily_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    avg_processing_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    slot_bookings: Mapped[list["SlotBooking"]] = relationship(
        "SlotBooking", back_populates="centre"
    )
    queue_entries: Mapped[list["QueueEntry"]] = relationship(
        "QueueEntry", back_populates="centre"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="centre"
    )
    alert_logs: Mapped[list["AlertLog"]] = relationship(
        "AlertLog", back_populates="centre"
    )
