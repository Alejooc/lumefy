from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID

class POSProduct(BaseModel):
    id: UUID
    name: str
    sku: Optional[str] = None
    barcode: Optional[str] = None
    price: float
    stock: float
    category_id: Optional[UUID] = None
    category_name: Optional[str] = None
    image_url: Optional[str] = None

class POSCartItem(BaseModel):
    product_id: UUID
    quantity: float
    price: float
    discount: float = 0.0

class POSCheckout(BaseModel):
    branch_id: UUID
    client_id: Optional[UUID] = None
    items: List[POSCartItem]
    payment_method: str # CASH, CARD, MIXED
    amount_paid: float
    notes: Optional[str] = None
