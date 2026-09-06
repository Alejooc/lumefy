from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


BillingStatus = Literal["PENDING", "PAID", "REJECTED", "CANCELLED"]


class SaaSBillingRecordCreate(BaseModel):
    plan_code: str = Field(min_length=1, max_length=64)
    period_start: datetime
    period_end: datetime
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=8)
    payment_method: str | None = Field(default="MANUAL_TRANSFER", max_length=40)
    reference: str | None = Field(default=None, max_length=160)
    proof_url: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("plan_code", mode="before")
    @classmethod
    def normalize_plan_code(cls, value: str) -> str:
        return str(value or "").strip().upper()

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return str(value).strip().upper() if value else None

    @model_validator(mode="after")
    def validate_period(self) -> "SaaSBillingRecordCreate":
        if self.period_end <= self.period_start:
            raise ValueError("period_end debe ser posterior a period_start")
        return self


class SaaSBillingVerification(BaseModel):
    status: Literal["PAID", "REJECTED", "CANCELLED"]
    reference: str | None = Field(default=None, max_length=160)
    proof_url: str | None = Field(default=None, max_length=500)
    rejection_reason: str | None = Field(default=None, max_length=4000)
    notes: str | None = Field(default=None, max_length=4000)


class SaaSBillingRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    plan_code: str
    period_start: datetime
    period_end: datetime
    amount: Decimal
    currency: str
    status: BillingStatus
    payment_method: str | None = None
    reference: str | None = None
    proof_url: str | None = None
    notes: str | None = None
    rejection_reason: str | None = None
    paid_at: datetime | None = None
    verified_by_user_id: UUID | None = None
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SaaSBillingPortfolioItem(BaseModel):
    company_id: UUID
    company_name: str
    plan: str | None = None
    subscription_status: str | None = None
    valid_until: str | None = None
    is_active: bool
    billing_state: Literal["PAID", "PENDING", "OVERDUE", "DUE_SOON", "NO_RECORD"]
    latest_record: SaaSBillingRecordOut | None = None
