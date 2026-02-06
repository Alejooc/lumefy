from typing import Optional
from pydantic import BaseModel
from uuid import UUID

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[UUID] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(CategoryBase):
    pass

class Category(CategoryBase):
    id: UUID
    company_id: Optional[UUID] = None

    class Config:
        from_attributes = True
