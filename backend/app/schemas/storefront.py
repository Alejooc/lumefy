from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class Msg(BaseModel):
    msg: str


class StorefrontBase(BaseModel):
    name: str
    slug: str
    subdomain: Optional[str] = None
    is_enabled: bool = False
    theme_key: str = "modern"
    theme_settings: dict = Field(default_factory=dict)
    checkout_settings: dict = Field(default_factory=dict)
    seo_settings: dict = Field(default_factory=dict)
    currency: str = "USD"
    language: str = "es"


class StorefrontCreate(StorefrontBase):
    pass


class StorefrontUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    subdomain: Optional[str] = None
    is_enabled: Optional[bool] = None
    theme_key: Optional[str] = None
    theme_settings: Optional[dict] = None
    checkout_settings: Optional[dict] = None
    seo_settings: Optional[dict] = None
    currency: Optional[str] = None
    language: Optional[str] = None


class Storefront(StorefrontBase):
    id: UUID
    company_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class StorefrontDomainBase(BaseModel):
    domain: str
    is_primary: bool = False
    is_verified: bool = False


class StorefrontDomainCreate(StorefrontDomainBase):
    storefront_id: UUID


class StorefrontDomainUpdate(BaseModel):
    domain: Optional[str] = None
    is_primary: Optional[bool] = None
    is_verified: Optional[bool] = None


class StorefrontDomain(StorefrontDomainBase):
    id: UUID
    storefront_id: UUID
    company_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class StoreCollectionBase(BaseModel):
    storefront_id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_visible: bool = True
    is_featured: bool = False
    sort_order: int = 0


class StoreCollectionCreate(StoreCollectionBase):
    pass


class StoreCollectionUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_visible: Optional[bool] = None
    is_featured: Optional[bool] = None
    sort_order: Optional[int] = None


class StoreCollection(StoreCollectionBase):
    id: UUID
    company_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class PublishedProductBase(BaseModel):
    storefront_id: UUID
    product_id: UUID
    custom_title: Optional[str] = None
    custom_description: Optional[str] = None
    slug: str
    price_override: Optional[float] = None
    compare_at_price: Optional[float] = None
    is_published: bool = True
    is_featured: bool = False
    show_stock: bool = True
    sort_order: int = 0
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None


class PublishedProductCreate(PublishedProductBase):
    pass


class PublishedProductUpdate(BaseModel):
    custom_title: Optional[str] = None
    custom_description: Optional[str] = None
    slug: Optional[str] = None
    price_override: Optional[float] = None
    compare_at_price: Optional[float] = None
    is_published: Optional[bool] = None
    is_featured: Optional[bool] = None
    show_stock: Optional[bool] = None
    sort_order: Optional[int] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None


class PublishedProduct(PublishedProductBase):
    id: UUID
    base_price: Optional[float] = None
    company_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class StoreCollectionProductBase(BaseModel):
    published_product_id: UUID
    sort_order: int = 0


class StoreCollectionProductCreate(StoreCollectionProductBase):
    pass


class StoreCollectionProduct(StoreCollectionProductBase):
    id: UUID
    collection_id: UUID
    company_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class StoreNavigationItemBase(BaseModel):
    storefront_id: UUID
    parent_id: Optional[UUID] = None
    label: str
    item_type: str = "collection"
    reference_id: Optional[UUID] = None
    url: Optional[str] = None
    sort_order: int = 0
    is_visible: bool = True


class StoreNavigationItemCreate(StoreNavigationItemBase):
    pass


class StoreNavigationItemUpdate(BaseModel):
    parent_id: Optional[UUID] = None
    label: Optional[str] = None
    item_type: Optional[str] = None
    reference_id: Optional[UUID] = None
    url: Optional[str] = None
    sort_order: Optional[int] = None
    is_visible: Optional[bool] = None


class StoreNavigationItem(StoreNavigationItemBase):
    id: UUID
    company_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class StorePaymentGatewayBase(BaseModel):
    storefront_id: UUID
    provider: str
    display_name: str
    is_enabled: bool = False
    is_sandbox: bool = True
    public_key: Optional[str] = None
    secret_key_encrypted: Optional[str] = None
    merchant_id: Optional[str] = None
    extra_config: dict = Field(default_factory=dict)
    sort_order: int = 0


class StorePaymentGatewayCreate(StorePaymentGatewayBase):
    pass


class StorePaymentGatewayUpdate(BaseModel):
    display_name: Optional[str] = None
    is_enabled: Optional[bool] = None
    is_sandbox: Optional[bool] = None
    public_key: Optional[str] = None
    secret_key_encrypted: Optional[str] = None
    merchant_id: Optional[str] = None
    extra_config: Optional[dict] = None
    sort_order: Optional[int] = None


class StorePaymentGateway(StorePaymentGatewayBase):
    id: UUID
    company_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class PublicStorefrontBranding(BaseModel):
    logo_url: Optional[str] = None
    support_phone: Optional[str] = None
    support_email: Optional[str] = None
    support_address: Optional[str] = None
    website: Optional[str] = None
    footer_text: Optional[str] = None
    social_links: dict = Field(default_factory=dict)
    promo_banners: list[dict] = Field(default_factory=list)


class PublicStorefront(BaseModel):
    id: UUID
    name: str
    slug: str
    subdomain: Optional[str] = None
    theme_key: str
    theme_settings: dict = Field(default_factory=dict)
    checkout_settings: dict = Field(default_factory=dict)
    seo_settings: dict = Field(default_factory=dict)
    currency: str
    language: str
    branding: PublicStorefrontBranding = Field(default_factory=PublicStorefrontBranding)


class PublicStoreNavigationItem(BaseModel):
    id: UUID
    parent_id: Optional[UUID] = None
    label: str
    item_type: str
    reference_id: Optional[UUID] = None
    url: Optional[str] = None
    sort_order: int


class PublicStorePaymentGateway(BaseModel):
    id: UUID
    provider: str
    display_name: str
    is_sandbox: bool = True
    sort_order: int = 0
    checkout_flow: str = "manual"
    public_config: dict = Field(default_factory=dict)


class PublicProduct(BaseModel):
    id: UUID
    product_id: UUID
    slug: str
    title: str
    description: Optional[str] = None
    category_name: Optional[str] = None
    brand_name: Optional[str] = None
    product_type: Optional[str] = None
    available_sizes: list[str] = Field(default_factory=list)
    available_colors: list[str] = Field(default_factory=list)
    image_url: Optional[str] = None
    gallery: list[str] = Field(default_factory=list)
    price: float
    base_price: float
    compare_at_price: Optional[float] = None
    is_featured: bool = False
    show_stock: bool = True
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None


class PublicCollection(BaseModel):
    id: UUID
    storefront_id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_featured: bool = False
    products: list[PublicProduct] = Field(default_factory=list)


class PublicCatalogCategory(BaseModel):
    name: str
    slug: str
    products: int
    is_refined: bool = False


class PublicCatalogFacet(BaseModel):
    value: str
    products: int
    is_refined: bool = False


class PublicCatalogProductType(BaseModel):
    name: str
    value: str
    products: int
    is_refined: bool = False


class PublicCatalogResponse(BaseModel):
    items: list[PublicProduct] = Field(default_factory=list)
    categories: list[PublicCatalogCategory] = Field(default_factory=list)
    product_types: list[PublicCatalogProductType] = Field(default_factory=list)
    sizes: list[PublicCatalogFacet] = Field(default_factory=list)
    colors: list[PublicCatalogFacet] = Field(default_factory=list)
    total_products: int = 0
    current_page: int = 1
    page_size: int = 12
    total_pages: int = 1
    selected_collection_name: Optional[str] = None


class PublicCheckoutItemInput(BaseModel):
    published_product_id: UUID
    quantity: float = 1


class PublicCheckoutCustomer(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=160)
    email: str
    phone: Optional[str] = Field(default=None, max_length=40)
    document_id: Optional[str] = Field(default=None, max_length=60)


class PublicCheckoutAddress(BaseModel):
    line1: str = Field(..., min_length=4, max_length=240)
    city: Optional[str] = Field(default=None, max_length=120)
    state: Optional[str] = Field(default=None, max_length=120)
    country: Optional[str] = Field(default=None, max_length=120)
    postal_code: Optional[str] = Field(default=None, max_length=40)


class PublicCheckoutPreviewRequest(BaseModel):
    items: list[PublicCheckoutItemInput] = Field(default_factory=list)
    shipping_amount: float = 0
    discount_amount: float = 0
    coupon_code: Optional[str] = None


class PublicCheckoutPreviewItem(BaseModel):
    published_product_id: UUID
    product_id: UUID
    slug: str
    title: str
    quantity: float
    unit_price: float
    line_subtotal: float


class PublicCheckoutPreviewResponse(BaseModel):
    currency: str
    items: list[PublicCheckoutPreviewItem] = Field(default_factory=list)
    subtotal: float
    discount: float
    shipping: float
    tax: float
    total: float


class PublicCheckoutCreateOrderRequest(BaseModel):
    items: list[PublicCheckoutItemInput] = Field(default_factory=list)
    customer: PublicCheckoutCustomer
    address: PublicCheckoutAddress
    notes: Optional[str] = Field(default=None, max_length=2000)
    payment_provider: str = Field(..., min_length=2, max_length=80)
    shipping_amount: float = 0
    discount_amount: float = 0
    coupon_code: Optional[str] = Field(default=None, max_length=80)
    idempotency_key: Optional[str] = Field(default=None, min_length=8, max_length=120)


class PublicCheckoutCreateOrderResponse(BaseModel):
    order_id: UUID
    order_code: str
    status: str
    currency: str
    subtotal: float
    discount: float
    shipping: float
    tax: float
    total: float
    payment_provider: str
    payment_status: str


class PublicPaymentIntentRequest(BaseModel):
    provider: str
    amount: float
    currency: str
    order_id: Optional[UUID] = None
    customer_email: Optional[str] = None
    customer_full_name: Optional[str] = None
    customer_phone: Optional[str] = None
    shipping_address: dict = Field(default_factory=dict)
    return_url: Optional[str] = None


class PublicPaymentIntentResponse(BaseModel):
    provider: str
    flow: str = "manual"
    mode: str
    amount: float
    currency: str
    external_reference: str
    checkout_url: Optional[str] = None
    public_key: Optional[str] = None
    merchant_id: Optional[str] = None
    instructions: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    provider_payload: dict = Field(default_factory=dict)


class PublicPaymentStatusResponse(BaseModel):
    provider: str
    transaction_id: str
    external_reference: Optional[str] = None
    status: str
    status_message: Optional[str] = None
    order_id: Optional[UUID] = None
    order_code: Optional[str] = None


class PublicStorefrontAccountUser(BaseModel):
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    created_at: datetime


class PublicStorefrontAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: PublicStorefrontAccountUser


class PublicStorefrontRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class PublicStorefrontLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class PublicStorefrontAccountProfileUpdate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)


class PublicStorefrontAccountPasswordChange(BaseModel):
    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class PublicStorefrontPasswordRecoveryRequest(BaseModel):
    email: EmailStr


class PublicStorefrontPasswordResetRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class PublicStorefrontContactRequest(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=60)
    last_name: str = Field(..., min_length=2, max_length=60)
    email: EmailStr
    subject: Optional[str] = Field(default=None, max_length=160)
    phone: Optional[str] = Field(default=None, max_length=40)
    message: str = Field(..., min_length=10, max_length=4000)


class PublicStorefrontAccountOrder(BaseModel):
    order_id: UUID
    order_code: str
    created_at: datetime
    status: str
    title: str
    total: float
    currency: str
