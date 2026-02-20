from pydantic import BaseModel
from uuid import UUID
from typing import Optional, List
from datetime import datetime
from app.models.purchase import PurchaseStatus
from app.schemas.supplier import Supplier
from app.schemas.branch import Branch
from app.schemas.product import Product
from app.schemas.product_variant import ProductVariant

class PurchaseOrderItemBase(BaseModel):
    product_id: UUID
    variant_id: Optional[UUID] = None
    quantity: float
    unit_cost: float

class PurchaseOrderItemCreate(PurchaseOrderItemBase):
    pass

class ReceiveItemInput(BaseModel):
    item_id: UUID
    qty_received: float

class PurchaseOrderItem(PurchaseOrderItemBase):
    id: UUID
    purchase_id: UUID
    subtotal: float
    received_qty: float = 0.0
    product: Optional[Product] = None
    variant: Optional[ProductVariant] = None

    class Config:
        from_attributes = True

class ReceiveInput(BaseModel):
    items: List[ReceiveItemInput]

class PurchaseOrderBase(BaseModel):
    supplier_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    notes: Optional[str] = None
    expected_date: Optional[datetime] = None
    order_date: Optional[datetime] = None
    reference_number: Optional[str] = None

class PurchaseOrderCreate(PurchaseOrderBase):
    payment_method: Optional[str] = "CASH"
    items: List[PurchaseOrderItemCreate] = []

class PurchaseOrderUpdate(BaseModel):
    supplier_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    notes: Optional[str] = None
    expected_date: Optional[datetime] = None
    status: Optional[PurchaseStatus] = None
    payment_method: Optional[str] = None

class PurchaseOrder(PurchaseOrderBase):
    id: UUID
    status: PurchaseStatus
    payment_method: str
    total_amount: float
    order_date: datetime
    reference_number: Optional[str] = None
    created_at: datetime
    company_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    items: List[PurchaseOrderItem] = []
    supplier: Optional[Supplier] = None
    branch: Optional[Branch] = None

    class Config:
        from_attributes = True

class PurchaseOrderSummary(PurchaseOrderBase):
    id: UUID
    status: PurchaseStatus
    total_amount: float
    created_at: datetime
    company_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    supplier: Optional[Supplier] = None
    branch: Optional[Branch] = None

    class Config:
        from_attributes = True
