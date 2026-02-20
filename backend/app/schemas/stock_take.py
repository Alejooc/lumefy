from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from enum import Enum

from app.schemas.branch import Branch
from app.schemas.product import Product


class StockTakeStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# --- Item Schemas ---
class StockTakeItemBase(BaseModel):
    product_id: UUID
    system_qty: float = 0.0
    counted_qty: Optional[float] = None
    difference: float = 0.0


class StockTakeItemCreate(BaseModel):
    product_id: UUID
    system_qty: float = 0.0


class StockTakeItemUpdate(BaseModel):
    id: UUID
    counted_qty: Optional[float] = None


class StockTakeItem(StockTakeItemBase):
    id: UUID
    stock_take_id: UUID
    product: Optional[Product] = None

    class Config:
        from_attributes = True


# --- Stock Take Schemas ---
class StockTakeCreate(BaseModel):
    branch_id: UUID
    notes: Optional[str] = None


class StockTakeCountUpdate(BaseModel):
    items: List[StockTakeItemUpdate]


class StockTakeSummary(BaseModel):
    id: UUID
    branch_id: UUID
    status: StockTakeStatus
    notes: Optional[str] = None
    created_at: datetime
    branch: Optional[Branch] = None
    item_count: Optional[int] = None

    class Config:
        from_attributes = True


class StockTake(BaseModel):
    id: UUID
    branch_id: UUID
    user_id: Optional[UUID] = None
    status: StockTakeStatus
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    branch: Optional[Branch] = None
    items: List[StockTakeItem] = []

    class Config:
        from_attributes = True
