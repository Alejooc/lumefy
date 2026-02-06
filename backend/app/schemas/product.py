from typing import Optional
from pydantic import BaseModel
from uuid import UUID

class ProductBase(BaseModel):
    name: str
    sku: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None
    price: float = 0.0
    cost: float = 0.0
    track_inventory: bool = True
    min_stock: float = 0.0
    category_id: Optional[UUID] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(ProductBase):
    pass

class Product(ProductBase):
    id: UUID
    company_id: Optional[UUID] = None

    class Config:
        from_attributes = True
