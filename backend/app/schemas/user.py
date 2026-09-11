"""Pydantic schemas for User and FarmerProfile."""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator
from app.models.user import UserRole


# ─── User schemas ──────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str
    mobile: str
    aadhaar_number: Optional[str] = None
    role: UserRole
    password: str

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        digits = v.replace("+91", "").replace("-", "").replace(" ", "")
        if not digits.isdigit() or len(digits) != 10:
            raise ValueError("Mobile must be a 10-digit Indian number")
        return digits

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class UserUpdate(BaseModel):
    name: Optional[str] = None
    mobile: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    mobile: str
    role: UserRole
    assigned_centre_id: Optional[uuid.UUID] = None
    created_at: datetime


# ─── FarmerProfile schemas ─────────────────────────────────────────────────────

class FarmerProfileCreate(BaseModel):
    village: str
    district: str
    state: str
    land_holding: float = 0.0
    bank_account_number: Optional[str] = None
    bank_ifsc_code: Optional[str] = None
    registry_number: Optional[str] = None


class FarmerProfileUpdate(BaseModel):
    village: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    land_holding: Optional[float] = None
    bank_account_number: Optional[str] = None
    bank_ifsc_code: Optional[str] = None
    registry_number: Optional[str] = None


class FarmerProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    village: str
    district: str
    state: str
    land_holding: float
    bank_ifsc_code: Optional[str] = None
    registry_number: Optional[str] = None
    created_at: datetime


class FarmerWithProfileResponse(UserResponse):
    farmer_profile: Optional[FarmerProfileResponse] = None


# ─── Auth schemas ──────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    mobile: str
    aadhaar_number: Optional[str] = None
    role: UserRole
    password: str
    farmer_profile: Optional[FarmerProfileCreate] = None

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        digits = v.replace("+91", "").replace("-", "").replace(" ", "")
        if not digits.isdigit() or len(digits) != 10:
            raise ValueError("Mobile must be a 10-digit Indian number")
        return digits


class LoginRequest(BaseModel):
    mobile: str
    password: str
    role: Optional[UserRole] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str


# ─── Timeline ─────────────────────────────────────────────────────────────────

class TimelineEvent(BaseModel):
    stage: str
    label: str
    status: str  # "completed" | "active" | "pending"
    timestamp: Optional[datetime] = None
    detail: Optional[str] = None
