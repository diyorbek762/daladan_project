"""
Daladan Platform — Escrow Payment Pydantic Schemas
Request/response models for the trustless escrow release endpoint.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class EscrowReleaseRequest(BaseModel):
    """Input for releasing held escrow funds."""

    model_config = {"extra": "forbid"}

    deal_id: UUID = Field(
        ...,
        description="UUID of the deal group whose escrow to release",
    )
    pin: str = Field(
        ...,
        min_length=4,
        max_length=8,
        description="Cryptographic PIN for authorization (4-8 digits)",
    )
    idempotency_key: Optional[str] = Field(
        None,
        max_length=64,
        description="Unique key to prevent duplicate releases",
    )

    @field_validator("pin")
    @classmethod
    def pin_must_be_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("PIN must contain only digits")
        return v


class BalanceCredit(BaseModel):
    """Details of a balance credit."""

    user_id: str
    user_name: str
    role: str
    amount: float
    percentage: float


class EscrowReleaseResponse(BaseModel):
    """Result of a successful escrow release."""

    status: str = Field("funds_released", description="New escrow status")
    deal_number: int
    deal_title: str
    escrow_id: str
    amount: float = Field(..., description="Total escrow amount")
    currency: str = Field("USD")
    producer_credit: BalanceCredit
    driver_credit: BalanceCredit
    released_at: datetime
    idempotency_key: Optional[str] = None
    message: str = Field(..., description="Human-readable confirmation")


class EscrowStatusResponse(BaseModel):
    """Current status of an escrow transaction."""

    escrow_id: str
    deal_number: int
    amount: float
    currency: str
    status: str
    payer: Optional[str] = None
    payee: Optional[str] = None
    created_at: datetime
    released_at: Optional[datetime] = None
