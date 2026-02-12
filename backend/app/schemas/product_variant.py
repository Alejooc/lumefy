from typing import Optional
from pydantic import BaseModel
from uuid import UUID

class ProductVariantBase(BaseModel):
    name: str
    sku: Optional[str] = None
    barcode: Optional[str] = None
    price_extra: float = 0.0
    cost_extra: float = 0.0
    weight: Optional[float] = None

class ProductVariantCreate(ProductVariantBase):
    pass

class ProductVariantUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    price_extra: Optional[float] = None
    cost_extra: Optional[float] = None
    weight: Optional[float] = None

class ProductVariant(ProductVariantBase):
    id: UUID
    product_id: UUID

    class Config:
        from_attributes = True
