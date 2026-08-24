from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional, List, Literal
from app.models.pricelist import PriceListType

# Price List Item Schemas
class PriceListItemBase(BaseModel):
    product_id: UUID
    variant_id: Optional[UUID] = None
    min_quantity: float = 0.0
    price: Optional[float] = None

class PriceListItemCreate(PriceListItemBase):
    pass

class PriceListItemUpdate(BaseModel):
    min_quantity: Optional[float] = None
    price: Optional[float] = None

class PriceListItem(PriceListItemBase):
    id: UUID
    pricelist_id: UUID

    class Config:
        from_attributes = True

# Price List Schemas
class PriceListBase(BaseModel):
    name: str
    type: PriceListType = PriceListType.SALE
    currency: str = "USD"
    active: bool = True
    source_id: Optional[UUID] = None
    pricing_mode: Literal["FIXED", "MARKUP_PERCENT", "MARKUP_AMOUNT"] = "FIXED"
    base_source: Literal["INTERNAL_PRICE", "INTERNAL_COST", "EXTERNAL_PRICE", "EXTERNAL_COST"] = "INTERNAL_PRICE"
    adjustment_value: float = 0.0
    rounding_step: float = 0.0
    min_margin_percent: Optional[float] = None

class PriceListCreate(PriceListBase):
    items: List[PriceListItemCreate] = []

class PriceListUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[PriceListType] = None
    currency: Optional[str] = None
    active: Optional[bool] = None
    source_id: Optional[UUID] = None
    pricing_mode: Optional[Literal["FIXED", "MARKUP_PERCENT", "MARKUP_AMOUNT"]] = None
    base_source: Optional[Literal["INTERNAL_PRICE", "INTERNAL_COST", "EXTERNAL_PRICE", "EXTERNAL_COST"]] = None
    adjustment_value: Optional[float] = None
    rounding_step: Optional[float] = None
    min_margin_percent: Optional[float] = None

class PriceList(PriceListBase):
    id: UUID
    items: List[PriceListItem] = []

    class Config:
        from_attributes = True


class PriceListGlobalAdjustment(BaseModel):
    percent: float = Field(ge=-100, le=10000)
    base_source: Optional[Literal["INTERNAL_PRICE", "INTERNAL_COST", "EXTERNAL_PRICE", "EXTERNAL_COST"]] = None
    preserve_overrides: bool = True
    rounding_step: Optional[float] = None
    min_margin_percent: Optional[float] = None


class PriceListImportResult(BaseModel):
    dry_run: bool
    rows_received: int
    rows_applied: int
    rows_created: int
    rows_updated: int
    rows_cleared: int
    rows_failed: int
    errors: List[str] = []
