from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class ClientBase(BaseModel):
    name: str 
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True

class ClientCreate(ClientBase):
    pass

class ClientUpdate(ClientBase):
    name: Optional[str] = None
    is_active: Optional[bool] = None

class Client(ClientBase):
    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
