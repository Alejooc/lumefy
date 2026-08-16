from typing import Any, Optional
from pydantic import BaseModel
from uuid import UUID

class ProductVariantBase(BaseModel):
    name: str
    sku: Optional[str] = None
    barcode: Optional[str] = None
    price_extra: float = 0.0
    cost_extra: float = 0.0
    price: Optional[float] = None
    cost: Optional[float] = None
    attributes: dict[str, Any] = {}
    weight: Optional[float] = None

class ProductVariantCreate(ProductVariantBase):
    pass

class ProductVariantUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    price_extra: Optional[float] = None
    cost_extra: Optional[float] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    attributes: Optional[dict[str, Any]] = None
    weight: Optional[float] = None

class ProductVariant(ProductVariantBase):
    id: UUID
    product_id: UUID
    stock_quantity: Optional[float] = None
    available_stock: Optional[float] = None

    class Config:
        from_attributes = True
