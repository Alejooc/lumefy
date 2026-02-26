from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from enum import Enum

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


class POSSessionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class POSSessionVisibilityScope(str, Enum):
    OWN = "own"
    BRANCH = "branch"
    COMPANY = "company"


class POSSessionOpenIn(BaseModel):
    branch_id: UUID
    opening_amount: float = 0.0
    opening_note: Optional[str] = None


class POSSessionCloseIn(BaseModel):
    counted_amount: float
    closing_note: Optional[str] = None

class POSSessionReopenIn(BaseModel):
    reason: str


class POSSessionOut(BaseModel):
    id: UUID
    branch_id: UUID
    user_id: UUID
    status: POSSessionStatus
    opened_at: datetime
    closed_at: Optional[datetime] = None
    opening_amount: float
    counted_amount: float
    expected_amount: float
    over_short: float
    closing_note: Optional[str] = None
    cash_sales_total: float = 0.0

    class Config:
        from_attributes = True


class POSSessionListItem(BaseModel):
    id: UUID
    branch_id: UUID
    branch_name: Optional[str] = None
    user_id: UUID
    user_name: Optional[str] = None
    status: POSSessionStatus
    opened_at: datetime
    closed_at: Optional[datetime] = None
    opening_amount: float
    expected_amount: float
    counted_amount: float
    over_short: float
    cash_sales_total: float = 0.0
    total_sales: float = 0.0
    transactions_count: int = 0


class POSSessionStatsOut(BaseModel):
    id: UUID
    branch_id: UUID
    branch_name: Optional[str] = None
    user_id: UUID
    user_name: Optional[str] = None
    status: POSSessionStatus
    opened_at: datetime
    closed_at: Optional[datetime] = None
    opening_amount: float
    expected_amount: float
    counted_amount: float
    over_short: float
    transactions_count: int = 0
    total_sales: float = 0.0
    cash_sales_total: float = 0.0
    card_sales_total: float = 0.0
    credit_sales_total: float = 0.0
    average_ticket: float = 0.0
    closing_audit: Optional[dict] = None
    reopen_audit: Optional[dict] = None
    can_reopen: bool = False


class POSVoidIn(BaseModel):
    reason: Optional[str] = None


class POSVoidOut(BaseModel):
    success: bool
    sale_id: UUID
    status: str
    detail: str


class POSConfigOut(BaseModel):
    show_sessions_manager: bool = True
    session_visibility_scope: POSSessionVisibilityScope = POSSessionVisibilityScope.BRANCH
    allow_multiple_open_sessions_per_branch: bool = True
    allow_enter_other_user_session: bool = False
    require_manager_for_void: bool = True
    allow_reopen_closed_sessions: bool = True
    over_short_alert_threshold: float = 20.0
