from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WarehouseBase(BaseModel):
    branch_id: UUID
    name: str = Field(min_length=2, max_length=100)
    code: str = Field(min_length=1, max_length=40)
    is_default: bool = False
    allows_ecommerce: bool = True


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    code: Optional[str] = Field(default=None, min_length=1, max_length=40)
    is_default: Optional[bool] = None
    allows_ecommerce: Optional[bool] = None


class Warehouse(WarehouseBase):
    id: UUID
    company_id: Optional[UUID] = None
    is_active: bool

    class Config:
        from_attributes = True
