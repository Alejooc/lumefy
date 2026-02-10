from pydantic import BaseModel
from uuid import UUID
from typing import Optional, List
from datetime import datetime
from app.models.purchase import PurchaseStatus

class PurchaseOrderItemBase(BaseModel):
    product_id: UUID
    quantity: float
    unit_cost: float

class PurchaseOrderItemCreate(PurchaseOrderItemBase):
    pass

class PurchaseOrderItem(PurchaseOrderItemBase):
    id: UUID
    purchase_id: UUID
    subtotal: float

    class Config:
        from_attributes = True

class PurchaseOrderBase(BaseModel):
    supplier_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    notes: Optional[str] = None
    expected_date: Optional[datetime] = None

class PurchaseOrderCreate(PurchaseOrderBase):
    items: List[PurchaseOrderItemCreate] = []

class PurchaseOrderUpdate(BaseModel):
    status: Optional[PurchaseStatus] = None
    notes: Optional[str] = None

class PurchaseOrder(PurchaseOrderBase):
    id: UUID
    status: PurchaseStatus
    total_amount: float
    created_at: datetime
    company_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    items: List[PurchaseOrderItem] = []

    class Config:
        from_attributes = True
