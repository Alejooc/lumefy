from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from app.schemas.product import Product
from app.schemas.user import User
from app.schemas.branch import Branch
from app.schemas.client import Client # Added Import

# --- Payment Schemas ---
class PaymentBase(BaseModel):
    method: str
    amount: float
    reference: Optional[str] = None

class PaymentCreate(PaymentBase):
    pass

class Payment(PaymentBase):
    id: UUID
    sale_id: UUID
    
    class Config:
        from_attributes = True

# --- SaleItem Schemas ---
class SaleItemBase(BaseModel):
    product_id: UUID
    quantity: float
    price: float
    discount: float = 0.0

class SaleItemCreate(SaleItemBase):
    pass # total calculated by backend

class SaleItem(SaleItemBase):
    id: UUID
    sale_id: UUID
    total: float
    quantity_picked: float = 0.0
    product: Optional[Product] = None
    
    class Config:
        from_attributes = True

# --- Sale Schemas ---
class SaleBase(BaseModel):
    branch_id: UUID
    client_id: Optional[UUID] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    shipping_address: Optional[str] = None
    valid_until: Optional[datetime] = None

class SaleCreate(SaleBase):
    items: List[SaleItemCreate]
    payments: Optional[List[PaymentCreate]] = [] # Optional for Quotes/Orders
    status: Optional[str] = "DRAFT"
    # user_id comes from token

class Sale(SaleBase):
    id: UUID
    user_id: UUID
    status: str
    subtotal: float
    tax: float
    discount: float
    shipping_cost: float
    total: float
    created_at: datetime
    updated_at: datetime
    
    # Delivery fields
    delivered_at: Optional[datetime] = None
    delivery_notes: Optional[str] = None
    delivery_evidence_url: Optional[str] = None
    completed_at: Optional[datetime] = None
    
    items: List[SaleItem] = []
    payments: List[Payment] = []
    user: Optional[User] = None
    branch: Optional[Branch] = None
    client: Optional[Client] = None
    
    class Config:
        from_attributes = True

class SaleSummary(SaleBase):
    id: UUID
    user_id: UUID
    status: str
    subtotal: float
    tax: float
    discount: float
    shipping_cost: float
    total: float
    created_at: datetime
    updated_at: datetime
    delivered_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    user: Optional[User] = None
    branch: Optional[Branch] = None
    client: Optional[Client] = None
    
    class Config:
        from_attributes = True

# --- Delivery Confirmation ---
class DeliveryConfirmation(BaseModel):
    notes: Optional[str] = None
    evidence_url: Optional[str] = None

class ClientSalesResponse(BaseModel):
    total: int
    items: List[SaleSummary]
