from typing import Optional
from pydantic import BaseModel
from uuid import UUID

class BranchBase(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_warehouse: bool = True
    allow_pos: bool = True

class BranchCreate(BranchBase):
    pass

class BranchUpdate(BranchBase):
    pass

class Branch(BranchBase):
    id: UUID
    company_id: Optional[UUID] = None
    is_active: bool

    class Config:
        from_attributes = True
