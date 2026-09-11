"""Auth router: register, login, refresh, me."""
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User, UserRole
from app.models.farmer_profile import FarmerProfile
from app.schemas.user import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshRequest,
    UserResponse, FarmerWithProfileResponse
)
from app.schemas.common import APIResponse
from app.utils.security import (
    hash_password, verify_password, hash_aadhaar,
    create_access_token, create_refresh_token, decode_refresh_token
)
from app.middleware.auth import CurrentUser

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=APIResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Register a new user. If role=FARMER, farmer_profile is required."""
    # Check mobile uniqueness
    existing = await db.execute(select(User).where(User.mobile == body.mobile))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Mobile number already registered")

    if body.role == UserRole.FARMER and not body.farmer_profile:
        raise HTTPException(status_code=400, detail="farmer_profile is required for FARMER role")

    user = User(
        id=uuid.uuid4(),
        name=body.name,
        mobile=body.mobile,
        role=body.role,
        password_hash=hash_password(body.password),
        aadhaar_number_hash=hash_aadhaar(body.aadhaar_number) if body.aadhaar_number else None,
    )
    db.add(user)
    await db.flush()  # get user.id

    if body.role == UserRole.FARMER and body.farmer_profile:
        fp_data = body.farmer_profile
        profile = FarmerProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            village=fp_data.village,
            district=fp_data.district,
            state=fp_data.state,
            land_holding=fp_data.land_holding,
            bank_account_number_encrypted=fp_data.bank_account_number,
            bank_ifsc_code=fp_data.bank_ifsc_code,
            registry_number=fp_data.registry_number,
        )
        db.add(profile)

    await db.commit()
    await db.refresh(user)
    return APIResponse(success=True, data=UserResponse.model_validate(user))


@router.post("/login", response_model=APIResponse[TokenResponse])
async def login(
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Login with mobile + password. Returns access + refresh tokens."""
    result = await db.execute(select(User).where(User.mobile == body.mobile))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid mobile or password")

    if body.role and user.role != body.role:
        raise HTTPException(
            status_code=403,
            detail=f"This account has role '{user.role.value}', not '{body.role.value}'"
        )

    token_data = {"sub": str(user.id), "role": user.role.value}
    return APIResponse(
        success=True,
        data=TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
            user=UserResponse.model_validate(user),
        )
    )


@router.post("/refresh", response_model=APIResponse[TokenResponse])
async def refresh_token(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Refresh access token using a valid refresh token."""
    payload = decode_refresh_token(body.refresh_token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    token_data = {"sub": str(user.id), "role": user.role.value}
    return APIResponse(
        success=True,
        data=TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
            user=UserResponse.model_validate(user),
        )
    )


@router.get("/me", response_model=APIResponse[FarmerWithProfileResponse])
async def get_me(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Return current user with farmer profile if applicable."""
    result = await db.execute(
        select(User)
        .options(selectinload(User.farmer_profile))
        .where(User.id == current_user.id)
    )
    user = result.scalar_one()
    if user.role == UserRole.FARMER:
        fp_result = await db.execute(
            select(FarmerProfile).where(FarmerProfile.user_id == user.id)
        )
        profile = fp_result.scalar_one_or_none()
        user_data = FarmerWithProfileResponse.model_validate(user)
        if profile:
            from app.schemas.user import FarmerProfileResponse
            user_data.farmer_profile = FarmerProfileResponse.model_validate(profile)
        return APIResponse(success=True, data=user_data)
    return APIResponse(success=True, data=FarmerWithProfileResponse.model_validate(user))
