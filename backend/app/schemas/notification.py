"""Pydantic schemas for Notification."""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.notification import NotificationChannel


class NotificationCreate(BaseModel):
    user_id: uuid.UUID
    title: str
    body: str
    channel: NotificationChannel = NotificationChannel.APP


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    body: str
    channel: NotificationChannel
    is_read: bool
    created_at: datetime
