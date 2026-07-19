from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PurchaseRequestItemCreate(BaseModel):
    product_id: UUID
    quantity: float = Field(gt=0)


class PurchaseRequestCreate(BaseModel):
    branch_id: UUID
    priority: str = Field(default="NORMAL", max_length=20)
    requested_date: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, max_length=1000)
    items: List[PurchaseRequestItemCreate] = Field(min_length=1)


class PurchaseRequestStatusUpdate(BaseModel):
    status: str


class PurchaseRequestItemOut(PurchaseRequestItemCreate):
    id: UUID

    class Config:
        from_attributes = True


class SupplierQuoteItemCreate(BaseModel):
    product_id: UUID
    quantity: float = Field(gt=0)
    unit_cost: float = Field(ge=0)


class SupplierQuoteCreate(BaseModel):
    supplier_id: UUID
    reference_number: Optional[str] = Field(default=None, max_length=100)
    valid_until: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, max_length=1000)
    items: List[SupplierQuoteItemCreate] = Field(min_length=1)


class SupplierQuoteItemOut(SupplierQuoteItemCreate):
    id: UUID
    subtotal: float

    class Config:
        from_attributes = True


class SupplierQuoteOut(BaseModel):
    id: UUID
    request_id: UUID
    supplier_id: UUID
    status: str
    reference_number: Optional[str] = None
    valid_until: Optional[datetime] = None
    total_amount: float
    notes: Optional[str] = None
    created_at: datetime
    items: List[SupplierQuoteItemOut] = []

    class Config:
        from_attributes = True


class PurchaseRequestOut(BaseModel):
    id: UUID
    branch_id: UUID
    requested_by_id: UUID
    purchase_order_id: Optional[UUID] = None
    status: str
    priority: str
    requested_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    items: List[PurchaseRequestItemOut] = []
    quotes: List[SupplierQuoteOut] = []

    class Config:
        from_attributes = True
