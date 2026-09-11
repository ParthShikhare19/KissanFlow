"""SQLAlchemy ORM model for AlertLog."""
import uuid
import enum
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum, Boolean, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid
from app.database import Base


class AlertType(str, enum.Enum):
    DELAY = "DELAY"
    CONGESTION = "CONGESTION"
    ANOMALY = "ANOMALY"


class AlertSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertLog(Base):
    __tablename__ = "alert_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    centre_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("procurement_centres.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[AlertType] = mapped_column(SAEnum(AlertType), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(SAEnum(AlertSeverity), nullable=False)
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    centre: Mapped["ProcurementCentre"] = relationship("ProcurementCentre", back_populates="alert_logs")
