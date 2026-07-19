from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class InvoiceItemOut(BaseModel):
    id: UUID
    product_id: Optional[UUID] = None
    description: str
    quantity: float
    unit_price: float
    tax_rate: float
    subtotal: float

    class Config:
        from_attributes = True


class InvoicePaymentCreate(BaseModel):
    amount: float = Field(gt=0)
    method: str = Field(min_length=2, max_length=30)
    reference: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = Field(default=None, max_length=500)
    paid_at: Optional[datetime] = None


class InvoicePaymentOut(InvoicePaymentCreate):
    id: UUID
    invoice_id: UUID
    paid_at: datetime

    class Config:
        from_attributes = True


class InvoiceFromSourceCreate(BaseModel):
    type: str
    sale_id: Optional[UUID] = None
    purchase_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_source(self):
        invoice_type = self.type.upper()
        if invoice_type == "SALE" and self.sale_id and not self.purchase_id:
            return self
        if invoice_type == "PURCHASE" and self.purchase_id and not self.sale_id:
            return self
        raise ValueError("Una factura SALE requiere sale_id y una PURCHASE requiere purchase_id")


class InvoiceOut(BaseModel):
    id: UUID
    number: str
    type: str
    status: str
    branch_id: Optional[UUID] = None
    client_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    sale_id: Optional[UUID] = None
    purchase_id: Optional[UUID] = None
    issue_date: datetime
    due_date: Optional[datetime] = None
    posted_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    subtotal: float
    tax: float
    total: float
    amount_paid: float
    notes: Optional[str] = None
    created_at: datetime
    items: List[InvoiceItemOut] = []
    payments: List[InvoicePaymentOut] = []

    class Config:
        from_attributes = True
