import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import BaseModel
class StorefrontCoupon(BaseModel):
    __tablename__='storefront_coupons'
    storefront_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('storefronts.id'),index=True)
    code: Mapped[str]=mapped_column(String,index=True)
    discount_type: Mapped[str]=mapped_column(String,default='PERCENT')
    value: Mapped[float]=mapped_column(Float)
    minimum_amount: Mapped[float]=mapped_column(Float,default=0)
    starts_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    ends_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    is_enabled: Mapped[bool]=mapped_column(Boolean,default=True)
