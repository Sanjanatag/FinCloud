from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TransactionCreate(BaseModel):
    receiver_id: UUID
    amount: Decimal = Field(..., gt=0, le=10000)
    currency: str = Field(default="USD", max_length=3)
    description: Optional[str] = Field(None, max_length=500)


class TransactionResponse(BaseModel):
    id: UUID
    sender_id: UUID
    receiver_id: UUID
    amount: Decimal
    currency: str
    status: str
    description: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    transactions: list[TransactionResponse]
    total: int
    page: int
    page_size: int


class WalletResponse(BaseModel):
    id: UUID
    user_id: UUID
    balance: Decimal
    currency: str
    is_frozen: bool

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
