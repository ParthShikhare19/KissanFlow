"""Grievances router."""
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.grievance import Grievance, GrievanceStatus
from app.models.user import User, UserRole
from app.schemas.grievance import GrievanceCreate, GrievanceAssign, GrievanceResolve, GrievanceResponse
from app.schemas.common import APIResponse, PaginatedResponse, paginated_response
from app.middleware.auth import CurrentUser, require_role

router = APIRouter(tags=["grievances"])


async def _enrich(g: Grievance, db: AsyncSession) -> GrievanceResponse:
    resp = GrievanceResponse.model_validate(g)
    farmer_result = await db.execute(select(User).where(User.id == g.farmer_id))
    farmer = farmer_result.scalar_one_or_none()
    resp.farmer_name = farmer.name if farmer else None
    if g.assigned_to:
        officer_result = await db.execute(select(User).where(User.id == g.assigned_to))
        officer = officer_result.scalar_one_or_none()
        resp.assigned_officer_name = officer.name if officer else None
    return resp


@router.post("/", response_model=APIResponse[GrievanceResponse], status_code=201)
async def create_grievance(
    body: GrievanceCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    grievance = Grievance(
        id=uuid.uuid4(),
        farmer_id=current_user.id,
        slot_booking_id=body.slot_booking_id,
        category=body.category,
        description=body.description,
        status=GrievanceStatus.OPEN,
    )
    db.add(grievance)
    await db.commit()
    await db.refresh(grievance)
    return APIResponse(success=True, data=await _enrich(grievance, db))


@router.get("/", response_model=APIResponse[PaginatedResponse[GrievanceResponse]])
async def list_grievances(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[GrievanceStatus] = Query(None),
    farmer_id: Optional[uuid.UUID] = Query(None),
):
    query = select(Grievance)

    # Role-based filtering
    if current_user.role == UserRole.FARMER:
        query = query.where(Grievance.farmer_id == current_user.id)
    elif farmer_id:
        query = query.where(Grievance.farmer_id == farmer_id)

    if status:
        query = query.where(Grievance.status == status)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Grievance.created_at.desc()).offset(offset).limit(page_size)
    )
    items = [await _enrich(g, db) for g in result.scalars().all()]
    return APIResponse(success=True, data=paginated_response(items, total, page, page_size))


@router.get("/{grievance_id}", response_model=APIResponse[GrievanceResponse])
async def get_grievance(
    grievance_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    result = await db.execute(select(Grievance).where(Grievance.id == grievance_id))
    g = result.scalar_one_or_none()
    if not g:
        raise HTTPException(status_code=404, detail="Grievance not found")
    return APIResponse(success=True, data=await _enrich(g, db))


@router.put("/{grievance_id}/assign", response_model=APIResponse[GrievanceResponse])
async def assign_grievance(
    grievance_id: uuid.UUID,
    body: GrievanceAssign,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.MANDI_OFFICER, UserRole.GOVT_ADMIN]))],
):
    result = await db.execute(select(Grievance).where(Grievance.id == grievance_id))
    g = result.scalar_one_or_none()
    if not g:
        raise HTTPException(status_code=404, detail="Grievance not found")

    g.assigned_to = body.assigned_to
    g.status = GrievanceStatus.UNDER_REVIEW
    await db.commit()
    await db.refresh(g)
    return APIResponse(success=True, data=await _enrich(g, db))


@router.put("/{grievance_id}/resolve", response_model=APIResponse[GrievanceResponse])
async def resolve_grievance(
    grievance_id: uuid.UUID,
    body: GrievanceResolve,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.MANDI_OFFICER, UserRole.GOVT_ADMIN]))],
):
    result = await db.execute(select(Grievance).where(Grievance.id == grievance_id))
    g = result.scalar_one_or_none()
    if not g:
        raise HTTPException(status_code=404, detail="Grievance not found")

    g.resolution = body.resolution
    g.status = GrievanceStatus.RESOLVED
    g.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(g)
    return APIResponse(success=True, data=await _enrich(g, db))
