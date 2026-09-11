"""SQLAlchemy ORM model for Crop."""
import uuid
import enum
from sqlalchemy import String, Float, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class CropSeason(str, enum.Enum):
    RABI = "RABI"
    KHARIF = "KHARIF"
    ZAID = "ZAID"


class Crop(Base):
    __tablename__ = "crops"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    season: Mapped[CropSeason] = mapped_column(SAEnum(CropSeason), nullable=False)
    msp_per_quintal: Mapped[float] = mapped_column(Float, nullable=False)
    crop_code: Mapped[str] = mapped_column(String(5), unique=True, nullable=False)

    slot_bookings: Mapped[list["SlotBooking"]] = relationship(
        "SlotBooking", back_populates="crop"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="crop"
    )
