from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from app.schemas.product import Product
from app.schemas.user import User
from app.schemas.branch import Branch

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
    product: Optional[Product] = None
    
    class Config:
        from_attributes = True

# --- Sale Schemas ---
class SaleBase(BaseModel):
    branch_id: UUID
    client_id: Optional[UUID] = None
    payment_method: Optional[str] = None

class SaleCreate(SaleBase):
    items: List[SaleItemCreate]
    payments: List[PaymentCreate]
    # user_id comes from token

class Sale(SaleBase):
    id: UUID
    user_id: UUID
    status: str
    subtotal: float
    tax: float
    discount: float
    total: float
    created_at: datetime
    updated_at: datetime
    
    items: List[SaleItem] = []
    payments: List[Payment] = []
    user: Optional[User] = None
    branch: Optional[Branch] = None
    
    class Config:
        from_attributes = True
