from typing import Optional
from pydantic import BaseModel
from uuid import UUID

class BrandBase(BaseModel):
    name: str
    description: Optional[str] = None

class BrandCreate(BrandBase):
    pass

class BrandUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class Brand(BrandBase):
    id: UUID
    company_id: Optional[UUID] = None

    class Config:
        from_attributes = True
