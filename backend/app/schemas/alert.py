"""Pydantic schemas for AlertLog."""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.alert_log import AlertType, AlertSeverity


class AlertLogCreate(BaseModel):
    centre_id: uuid.UUID
    type: AlertType
    message: str
    severity: AlertSeverity


class AlertLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    centre_id: uuid.UUID
    type: AlertType
    message: str
    severity: AlertSeverity
    is_acknowledged: bool
    created_at: datetime

    centre_name: str | None = None
