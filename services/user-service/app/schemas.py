from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: str = Field(..., pattern=r"^[\w\.\-]+@[\w\.\-]+\.\w+$", max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    phone: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserWithWallet(UserResponse):
    wallet: Optional["WalletResponse"] = None


class WalletResponse(BaseModel):
    id: UUID
    balance: Decimal
    currency: str
    is_frozen: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
