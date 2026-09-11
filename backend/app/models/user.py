"""SQLAlchemy ORM model for User."""
import uuid
import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class UserRole(str, enum.Enum):
    FARMER = "FARMER"
    MANDI_STAFF = "MANDI_STAFF"
    MANDI_OFFICER = "MANDI_OFFICER"
    GOVT_ADMIN = "GOVT_ADMIN"
    CSC_OPERATOR = "CSC_OPERATOR"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    mobile: Mapped[str] = mapped_column(String(15), unique=True, nullable=False, index=True)
    aadhaar_number_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    farmer_profile: Mapped["FarmerProfile | None"] = relationship(
        "FarmerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    slot_bookings: Mapped[list["SlotBooking"]] = relationship(
        "SlotBooking", back_populates="farmer", foreign_keys="SlotBooking.farmer_id"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="farmer", foreign_keys="Transaction.farmer_id"
    )
    grievances: Mapped[list["Grievance"]] = relationship(
        "Grievance", back_populates="farmer", foreign_keys="Grievance.farmer_id"
    )
    assigned_grievances: Mapped[list["Grievance"]] = relationship(
        "Grievance", back_populates="assigned_officer", foreign_keys="Grievance.assigned_to"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user"
    )
