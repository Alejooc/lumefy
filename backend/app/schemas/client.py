from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import List, Dict, Any, Optional
import enum

class ClientBase(BaseModel):
    name: str 
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True
    
    # CRM Fields
    status: Optional[str] = "active"
    tags: Optional[Dict[str, Any]] = None
    last_interaction_at: Optional[datetime] = None

class ClientCreate(ClientBase):
    credit_limit: Optional[float] = 0.0

class ClientUpdate(ClientBase):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    credit_limit: Optional[float] = None
    status: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None

class Client(ClientBase):
    id: UUID
    company_id: UUID
    credit_limit: float
    current_balance: float
    created_at: datetime
    updated_at: datetime
    
    # New relationships or counts can go here
    activity_count: Optional[int] = 0
    total_sales: Optional[float] = 0.0

    class Config:
        from_attributes = True

# CRM Activities
class ActivityType(str, enum.Enum):
    CALL = "CALL"
    MEETING = "MEETING"
    EMAIL = "EMAIL"
    NOTE = "NOTE"
    SYSTEM = "SYSTEM"

class ActivityBase(BaseModel):
    type: ActivityType
    content: str

class ActivityCreate(ActivityBase):
    pass

class Activity(ActivityBase):
    id: UUID
    client_id: UUID
    user_id: UUID
    created_at: datetime
    user_name: Optional[str] = None

    class Config:
        from_attributes = True

class ClientStats(BaseModel):
    total_sales: float = 0.0
    order_count: int = 0
    average_order_value: float = 0.0
    last_sale_at: Optional[datetime] = None
    
class UnifiedTimelineItem(BaseModel):
    id: UUID
    type: str # ACTIVITY, LEDGER
    category: str # CALL, NOTE, CHARGE, PAYMENT etc.
    content: str
    amount: Optional[float] = None
    created_at: datetime
    user_name: Optional[str] = None



