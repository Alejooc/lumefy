from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID
from app.schemas.unit_of_measure import UnitOfMeasure as UnitOfMeasureSchema
from app.schemas.brand import Brand as BrandSchema
from app.schemas.product_variant import ProductVariant as ProductVariantSchema

class ProductBase(BaseModel):
    name: str
    internal_reference: Optional[str] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    product_type: str = "STORABLE"  # STORABLE, CONSUMABLE, SERVICE

    # Pricing
    price: float = 0.0
    cost: float = 0.0
    tax_rate: float = 0.0

    # Physical
    weight: Optional[float] = None
    volume: Optional[float] = None

    # Inventory
    track_inventory: bool = True
    min_stock: float = 0.0
    sale_ok: bool = True
    purchase_ok: bool = True

    # Foreign Keys
    category_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    unit_of_measure_id: Optional[UUID] = None
    purchase_uom_id: Optional[UUID] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    internal_reference: Optional[str] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    product_type: Optional[str] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    tax_rate: Optional[float] = None
    weight: Optional[float] = None
    volume: Optional[float] = None
    track_inventory: Optional[bool] = None
    min_stock: Optional[float] = None
    sale_ok: Optional[bool] = None
    purchase_ok: Optional[bool] = None
    category_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    unit_of_measure_id: Optional[UUID] = None
    purchase_uom_id: Optional[UUID] = None

class Product(ProductBase):
    id: UUID
    company_id: Optional[UUID] = None
    is_active: bool = True

    # Related objects
    brand: Optional[BrandSchema] = None
    unit_of_measure: Optional[UnitOfMeasureSchema] = None
    purchase_uom: Optional[UnitOfMeasureSchema] = None
    variants: List[ProductVariantSchema] = []

    class Config:
        from_attributes = True
