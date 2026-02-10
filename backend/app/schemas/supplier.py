from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class SupplierBase(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None

class SupplierCreate(SupplierBase):
    pass

class SupplierUpdate(SupplierBase):
    pass

class Supplier(SupplierBase):
    id: UUID
    company_id: Optional[UUID] = None

    class Config:
        from_attributes = True
