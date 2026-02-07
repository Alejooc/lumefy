from typing import Optional
from pydantic import BaseModel
from uuid import UUID

class BranchBase(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

class BranchCreate(BranchBase):
    pass

class BranchUpdate(BranchBase):
    pass

class Branch(BranchBase):
    id: UUID
    company_id: UUID
    is_active: bool

    class Config:
        from_attributes = True
