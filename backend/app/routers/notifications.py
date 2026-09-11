"""Notifications router."""
import uuid
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.database import get_db
from app.models.notification import Notification, NotificationChannel
from app.schemas.notification import NotificationResponse
from app.schemas.common import APIResponse, PaginatedResponse, paginated_response
from app.middleware.auth import CurrentUser
from app.models.user import UserRole

router = APIRouter(tags=["notifications"])


def _enforce_notification_access(current_user, user_id: uuid.UUID) -> None:
    if user_id != current_user.id and current_user.role not in [UserRole.MANDI_OFFICER, UserRole.GOVT_ADMIN]:
        raise HTTPException(status_code=403, detail="Cannot access another user's notifications")


@router.get("/{user_id}", response_model=APIResponse[PaginatedResponse[NotificationResponse]])
async def get_notifications(
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    channel: Optional[NotificationChannel] = Query(None),
):
    _enforce_notification_access(current_user, user_id)
    query = select(Notification).where(Notification.user_id == user_id)
    if channel:
        query = query.where(Notification.channel == channel)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Notification.created_at.desc()).offset(offset).limit(page_size)
    )
    items = [NotificationResponse.model_validate(n) for n in result.scalars().all()]
    return APIResponse(success=True, data=paginated_response(items, total, page, page_size))


@router.get("/{user_id}/unread-count", response_model=APIResponse[dict])
async def get_unread_count(
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    """True global unread count across all pages and filters (#15)."""
    _enforce_notification_access(current_user, user_id)
    count_result = await db.execute(
        select(func.count()).where(
            Notification.user_id == user_id,
            Notification.is_read == False,
        )
    )
    count = count_result.scalar() or 0
    return APIResponse(success=True, data={"unread_count": count})


@router.put("/{user_id}/read-all", response_model=APIResponse[dict])
async def mark_all_read(
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    """Mark every notification of the user as read in one statement (#14)."""
    _enforce_notification_access(current_user, user_id)
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read == False)
        .values(is_read=True)
    )
    await db.commit()
    return APIResponse(success=True, data={"marked_read": result.rowcount or 0})


@router.put("/{notification_id}/read", response_model=APIResponse[NotificationResponse])
async def mark_read(
    notification_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notif.user_id != current_user.id and current_user.role not in [UserRole.MANDI_OFFICER, UserRole.GOVT_ADMIN]:
        raise HTTPException(status_code=403, detail="Cannot update another user's notification")

    notif.is_read = True
    await db.commit()
    await db.refresh(notif)
    return APIResponse(success=True, data=NotificationResponse.model_validate(notif))
