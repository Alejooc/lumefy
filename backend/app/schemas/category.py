from typing import Optional, List
from pydantic import BaseModel, UUID4
from datetime import datetime

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[UUID4] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(CategoryBase):
    name: Optional[str] = None

class Category(CategoryBase):
    id: UUID4
    company_id: Optional[UUID4] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True
