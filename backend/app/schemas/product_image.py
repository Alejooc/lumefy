from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class ProductImageBase(BaseModel):
    image_url: str
    order: int = 0

class ProductImageCreate(ProductImageBase):
    pass

class ProductImageUpdate(ProductImageBase):
    pass

class ProductImage(ProductImageBase):
    id: UUID
    product_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
