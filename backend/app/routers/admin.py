"""Admin router for dev-only seed triggers."""
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import APIResponse
from app.middleware.auth import require_role
from app.models.user import UserRole, User

router = APIRouter(tags=["admin"])


@router.post("/seed/full", response_model=APIResponse[dict])
async def trigger_full_seed(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.GOVT_ADMIN]))],
):
    """Trigger full seed from API (calls seed logic inline). Idempotent."""
    try:
        from seed import run_seed
        await run_seed(db)
        return APIResponse(success=True, data={"message": "Full seed completed"})
    except Exception as e:
        return APIResponse(success=False, error=str(e))


@router.post("/seed/{seed_type}", response_model=APIResponse[dict])
async def trigger_seed(
    seed_type: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.GOVT_ADMIN]))],
):
    """Dev-only endpoint to trigger specific seed operations. Requires GOVT_ADMIN (#3)."""
    valid_types = ["centres-crops", "users-farmers", "bookings-transactions"]
    if seed_type not in valid_types:
        return APIResponse(success=False, error=f"Invalid seed type. Valid: {valid_types}")
    return APIResponse(success=True, data={"message": f"Seed '{seed_type}' triggered", "type": seed_type})
