from typing import Any, Optional, List, Literal
from pydantic import BaseModel, Field
from uuid import UUID
from app.schemas.unit_of_measure import UnitOfMeasure as UnitOfMeasureSchema
from app.schemas.brand import Brand as BrandSchema
from app.schemas.category import Category as CategorySchema
from app.schemas.product_variant import ProductVariant as ProductVariantSchema
from app.schemas.product_image import ProductImage as ProductImageSchema

class ProductBase(BaseModel):
    name: str
    internal_reference: Optional[str] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    attributes: dict[str, Any] = {}
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
    tracking_type: str = "NONE"
    min_stock: float = 0.0
    sale_ok: bool = True
    purchase_ok: bool = True
    visible_in_ecommerce: bool = False

    # Foreign Keys
    category_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    unit_of_measure_id: Optional[UUID] = None
    purchase_uom_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None

from app.schemas.product_image import ProductImageCreate

class ProductCreate(ProductBase):
    images: Optional[List[ProductImageCreate]] = []

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    internal_reference: Optional[str] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    attributes: Optional[dict[str, Any]] = None
    images: Optional[List[ProductImageCreate]] = None
    product_type: Optional[str] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    tax_rate: Optional[float] = None
    weight: Optional[float] = None
    volume: Optional[float] = None
    track_inventory: Optional[bool] = None
    tracking_type: Optional[str] = None
    min_stock: Optional[float] = None
    sale_ok: Optional[bool] = None
    purchase_ok: Optional[bool] = None
    visible_in_ecommerce: Optional[bool] = None
    category_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    unit_of_measure_id: Optional[UUID] = None
    purchase_uom_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None

class Product(ProductBase):
    id: UUID
    company_id: Optional[UUID] = None
    is_active: bool = True

    # Related objects
    brand: Optional[BrandSchema] = None
    unit_of_measure: Optional[UnitOfMeasureSchema] = None
    purchase_uom: Optional[UnitOfMeasureSchema] = None
    variants: List[ProductVariantSchema] = []
    images: List[ProductImageSchema] = []

    class Config:
        from_attributes = True


class ProductListItem(BaseModel):
    """Minimal row used by the admin product table.

    The editor endpoint remains the place for full descriptions, attributes,
    images and variants. Keeping those large fields out of every paginated
    table request prevents provider HTML from being transferred and parsed for
    products that are not being opened.
    """

    id: UUID
    company_id: Optional[UUID] = None
    is_active: bool = True
    name: str
    internal_reference: Optional[str] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    image_url: Optional[str] = None
    product_type: str = "STORABLE"
    price: float = 0.0
    cost: float = 0.0
    track_inventory: bool = True
    visible_in_ecommerce: bool = False
    category_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    category: Optional[CategorySchema] = None
    brand: Optional[BrandSchema] = None
    variant_count: int = 0

    class Config:
        from_attributes = True

    class Config:
        from_attributes = True


class ProductBulkDeleteRequest(BaseModel):
    """Products selected by the user for a guarded bulk deletion."""

    product_ids: List[UUID] = Field(min_length=1, max_length=500)
    force: bool = False


class ProductBulkDeleteBlocked(BaseModel):
    id: UUID
    name: str
    reasons: List[str]


class ProductBulkDeleteResponse(BaseModel):
    requested: int
    deleted: int
    deleted_ids: List[UUID]
    blocked: List[ProductBulkDeleteBlocked]
    not_found: List[UUID]
    archived: int = 0
    archived_ids: List[UUID] = Field(default_factory=list)


class ProductBulkRestoreArchivedRequest(BaseModel):
    """Restore selected archived products, or all archived products when empty."""

    product_ids: List[UUID] = Field(default_factory=list, max_length=5000)


class ProductBulkRestoreArchivedResponse(BaseModel):
    requested: int
    restored: int
    restored_ids: List[UUID]
    not_found: List[UUID]


class ProductBulkDeleteArchivedRequest(BaseModel):
    """Archived products selected for permanent deletion, or all when empty."""

    product_ids: List[UUID] = Field(default_factory=list, max_length=5000)
    purge_inventory: bool = False
    exclude_product_ids: List[UUID] = Field(default_factory=list, max_length=20000)
    limit: int = Field(default=25, ge=1, le=100)


class ProductPage(BaseModel):
    """A server-paginated product collection for catalog screens."""

    items: List[ProductListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class ProductBulkDeleteAllRequest(BaseModel):
    """Optional filters for a whole-catalog deletion."""

    search: Optional[str] = None
    category_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    product_type: Optional[str] = None
    force: bool = False


class ProductPurgeAllRequest(BaseModel):
    """Explicit confirmation for the irreversible catalog purge.

    This endpoint is intentionally separate from guarded deletion.  A normal
    delete preserves business history; a purge is only for an operator who
    explicitly wants to empty the catalog and its product lines everywhere.
    """

    confirmation: Literal["PURGE_CATALOG"]
    search: Optional[str] = None
    category_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    product_type: Optional[str] = None


class ProductBulkImageUrlRequest(BaseModel):
    """Complete product image paths with a trusted URL prefix.

    By default, already absolute URLs are kept untouched.  Callers can opt
    into replacing them when a previous integration stored the wrong base URL.
    """

    prefix: str = Field(min_length=1, max_length=2000)
    product_ids: Optional[List[UUID]] = Field(default=None, max_length=10000)
    replace_existing: bool = False


class ProductBulkImageUrlResponse(BaseModel):
    requested: int
    products_updated: int
    images_updated: int
    skipped_valid: int
    not_found: List[UUID]


class ProductBulkPublishRequest(BaseModel):
    """Products to publish; omit IDs to publish the whole active catalog."""

    product_ids: Optional[List[UUID]] = Field(default=None, max_length=10000)


class ProductBulkPublishResponse(BaseModel):
    requested: int
    published: int
    reactivated: int
    already_published: int
    not_found: List[UUID]
