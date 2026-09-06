from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class CouponIn(BaseModel):
    storefront_id: UUID
    code: str = Field(min_length=3, max_length=30)
    discount_type: str = "PERCENT"
    value: float = Field(gt=0)
    minimum_amount: float = Field(default=0, ge=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_enabled: bool = True


class CouponUpdate(BaseModel):
    storefront_id: UUID | None = None
    code: str | None = Field(default=None, min_length=3, max_length=30)
    discount_type: str | None = None
    value: float | None = Field(default=None, gt=0)
    minimum_amount: float | None = Field(default=None, ge=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_enabled: bool | None = None


class CouponOut(CouponIn):
    id: UUID
    is_active: bool = True

    class Config:
        from_attributes = True
