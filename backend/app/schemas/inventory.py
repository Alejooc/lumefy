from typing import Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import date, datetime
from enum import Enum

class MovementType(str, Enum):
    IN = "IN"
    OUT = "OUT"
    ADJ = "ADJ"
    TRF = "TRF"

# --- Inventory Stock Schemas ---
class InventoryBase(BaseModel):
    product_id: UUID
    branch_id: UUID
    quantity: float
    location: Optional[str] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[date] = None

class InventoryCreate(InventoryBase):
    pass

from app.schemas.product import Product
from app.schemas.branch import Branch

class Inventory(InventoryBase):
    id: UUID
    product: Optional[Product] = None
    branch: Optional[Branch] = None
    
    class Config:
        from_attributes = True

# --- Movement Schemas ---
class MovementBase(BaseModel):
    product_id: UUID
    branch_id: UUID
    type: MovementType
    quantity: float
    reason: Optional[str] = None
    reference_id: Optional[str] = None

class MovementCreate(MovementBase):
    pass # user_id will be injected by backend

from app.schemas.user import User

class Movement(MovementBase):
    id: UUID
    user_id: Optional[UUID] = None
    previous_stock: float
    new_stock: float
    created_at: datetime
    
    # Nested objects for display
    user: Optional[User] = None
    product: Optional[Product] = None
    branch: Optional[Branch] = None
    
    class Config:
        from_attributes = True
