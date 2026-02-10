from pydantic import BaseModel
from uuid import UUID
from typing import Optional, List
from app.models.pricelist import PriceListType

# Price List Item Schemas
class PriceListItemBase(BaseModel):
    product_id: UUID
    min_quantity: float = 0.0
    price: float

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

class PriceListCreate(PriceListBase):
    items: List[PriceListItemCreate] = []

class PriceListUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[PriceListType] = None
    currency: Optional[str] = None
    active: Optional[bool] = None

class PriceList(PriceListBase):
    id: UUID
    items: List[PriceListItem] = []

    class Config:
        from_attributes = True
