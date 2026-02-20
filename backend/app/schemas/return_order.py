from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from enum import Enum


class ReturnStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ReturnType(str, Enum):
    PARTIAL = "PARTIAL"
    TOTAL = "TOTAL"


# --- Create ---
class ReturnItemCreate(BaseModel):
    sale_item_id: UUID
    quantity: float  # quantity to return


class ReturnOrderCreate(BaseModel):
    sale_id: UUID
    reason: Optional[str] = None
    notes: Optional[str] = None
    items: List[ReturnItemCreate]


# --- Response ---
from app.schemas.product import Product
from app.schemas.user import User


class ReturnItemResponse(BaseModel):
    id: UUID
    sale_item_id: UUID
    product_id: UUID
    quantity_returned: float
    unit_price: float
    subtotal: float
    product: Optional[Product] = None

    class Config:
        from_attributes = True


class ReturnOrderResponse(BaseModel):
    id: UUID
    sale_id: UUID
    created_by: UUID
    return_type: str
    status: str
    reason: Optional[str] = None
    total_refund: float
    notes: Optional[str] = None
    created_at: datetime
    approved_at: Optional[datetime] = None
    items: List[ReturnItemResponse] = []
    creator: Optional[User] = None
    approver: Optional[User] = None

    class Config:
        from_attributes = True
