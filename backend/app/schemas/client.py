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
    credit_limit: Optional[float] = 0.0

class ClientUpdate(ClientBase):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    credit_limit: Optional[float] = None

class Client(ClientBase):
    id: UUID
    company_id: UUID
    credit_limit: float
    current_balance: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
