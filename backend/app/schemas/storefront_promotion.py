from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


PromotionTargetType = Literal["COLLECTION", "PRODUCT"]


class PromotionIn(BaseModel):
    storefront_id: UUID
    name: str = Field(min_length=2, max_length=120)
    target_type: PromotionTargetType
    collection_id: UUID | None = None
    published_product_id: UUID | None = None
    discount_percent: float = Field(gt=0, le=100)
    priority: int = Field(default=0, ge=0, le=1000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_enabled: bool = True

    @model_validator(mode="after")
    def validate_target(self) -> "PromotionIn":
        target_count = int(self.collection_id is not None) + int(self.published_product_id is not None)
        if target_count != 1:
            raise ValueError("Selecciona exactamente una colección o un producto")
        if self.target_type == "COLLECTION" and self.collection_id is None:
            raise ValueError("Una promoción de colección necesita una colección")
        if self.target_type == "PRODUCT" and self.published_product_id is None:
            raise ValueError("Una promoción de producto necesita un producto")
        if self.starts_at and self.ends_at and self.starts_at > self.ends_at:
            raise ValueError("La fecha inicial no puede ser posterior a la fecha final")
        return self


class PromotionUpdate(BaseModel):
    storefront_id: UUID | None = None
    name: str | None = Field(default=None, min_length=2, max_length=120)
    target_type: PromotionTargetType | None = None
    collection_id: UUID | None = None
    published_product_id: UUID | None = None
    discount_percent: float | None = Field(default=None, gt=0, le=100)
    priority: int | None = Field(default=None, ge=0, le=1000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_enabled: bool | None = None


class PromotionOut(BaseModel):
    id: UUID
    storefront_id: UUID
    name: str
    target_type: PromotionTargetType
    collection_id: UUID | None = None
    published_product_id: UUID | None = None
    collection_name: str | None = None
    product_name: str | None = None
    target_label: str
    discount_percent: float
    priority: int
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_enabled: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
