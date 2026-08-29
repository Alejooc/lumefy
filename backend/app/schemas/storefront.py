from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class Msg(BaseModel):
    msg: str


class PublicNewsletterSubscriptionRequest(BaseModel):
    email: EmailStr = Field(max_length=320)


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
    price_list_id: Optional[UUID] = None
    fulfillment_warehouse_id: Optional[UUID] = None


class StorefrontCreate(BaseModel):
    """Public create contract; technical URLs are generated server-side."""
    name: str
    is_enabled: bool = False
    theme_key: str = "modern"
    theme_settings: dict = Field(default_factory=dict)
    checkout_settings: dict = Field(default_factory=dict)
    seo_settings: dict = Field(default_factory=dict)
    currency: str = "USD"
    language: str = "es"
    price_list_id: Optional[UUID] = None
    fulfillment_warehouse_id: Optional[UUID] = None


class StorefrontUpdate(BaseModel):
    name: Optional[str] = None
    is_enabled: Optional[bool] = None
    theme_key: Optional[str] = None
    theme_settings: Optional[dict] = None
    checkout_settings: Optional[dict] = None
    seo_settings: Optional[dict] = None
    currency: Optional[str] = None
    language: Optional[str] = None
    price_list_id: Optional[UUID] = None
    fulfillment_warehouse_id: Optional[UUID] = None


class StorefrontThemeDraftUpdate(BaseModel):
    document: dict = Field(default_factory=dict)
    expected_draft_version: int = Field(default=1, ge=0)


class StorefrontThemePublishRequest(BaseModel):
    expected_draft_version: Optional[int] = Field(default=None, ge=0)


class StorefrontThemePreviewSession(BaseModel):
    token: str
    expires_at: datetime
    preview_url: str
    template_key: str = "home"


class StorefrontMediaAsset(BaseModel):
    id: UUID
    storefront_id: UUID
    company_id: UUID
    url: str
    original_filename: str
    content_type: str
    size_bytes: int
    width: Optional[int] = None
    height: Optional[int] = None
    alt_text: Optional[str] = None
    created_at: datetime


class StorefrontThemeDocument(BaseModel):
    id: UUID
    storefront_id: UUID
    company_id: UUID
    template_key: str
    draft_document: dict = Field(default_factory=dict)
    published_document: dict = Field(default_factory=dict)
    draft_version: int
    published_version: int
    published_at: Optional[datetime] = None
    preview_url: Optional[str] = None


class StorefrontThemeRevision(BaseModel):
    id: UUID
    storefront_id: UUID
    template_key: str
    version: int
    document: dict = Field(default_factory=dict)
    operation: str
    created_at: datetime


class StorefrontThemeRestoreRequest(BaseModel):
    expected_draft_version: Optional[int] = Field(default=None, ge=0)


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


class StorefrontDomainCreate(StorefrontDomainBase):
    storefront_id: UUID


class StorefrontDomainUpdate(BaseModel):
    is_primary: Optional[bool] = None


class StorefrontDomain(StorefrontDomainBase):
    id: UUID
    storefront_id: UUID
    is_verified: bool
    verification_token: Optional[str] = None
    verification_record: Optional[str] = None
    verification_value: Optional[str] = None
    verified_at: Optional[datetime] = None
    provisioning_status: str = "PENDING_VERIFICATION"
    provisioning_attempts: int = 0
    provisioning_error: Optional[str] = None
    provisioning_next_attempt_at: Optional[datetime] = None
    provisioning_last_attempt_at: Optional[datetime] = None
    provisioned_at: Optional[datetime] = None
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
    slug: str
    is_published: bool = True
    is_featured: bool = False
    sort_order: int = 0
    seo_title: Optional[str] = Field(default=None, max_length=70)
    seo_description: Optional[str] = Field(default=None, max_length=320)


class PublishedProductCreate(PublishedProductBase):
    pass


class PublishedProductUpdate(BaseModel):
    is_published: Optional[bool] = None
    is_featured: Optional[bool] = None
    sort_order: Optional[int] = None
    seo_title: Optional[str] = Field(default=None, max_length=70)
    seo_description: Optional[str] = Field(default=None, max_length=320)


class PublishedProduct(PublishedProductBase):
    id: UUID
    base_price: Optional[float] = None
    product_name: Optional[str] = None
    product_description: Optional[str] = None
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


class StorefrontShippingDestinationBase(BaseModel):
    storefront_id: UUID
    country_code: str = "CO"
    state_code: Optional[str] = None
    state_name: str = Field(..., min_length=2, max_length=120)
    city_code: Optional[str] = None
    city_name: Optional[str] = Field(default=None, max_length=120)
    destination_type: str = "city"
    sort_order: int = 0


class StorefrontShippingDestinationCreate(StorefrontShippingDestinationBase):
    pass


class StorefrontShippingDestinationUpdate(BaseModel):
    country_code: Optional[str] = None
    state_code: Optional[str] = None
    state_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    city_code: Optional[str] = None
    city_name: Optional[str] = Field(default=None, max_length=120)
    destination_type: Optional[str] = None
    sort_order: Optional[int] = None


class StorefrontShippingDestination(StorefrontShippingDestinationBase):
    id: UUID
    company_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class StorefrontShippingMethodBase(BaseModel):
    storefront_id: UUID
    code: str = Field(..., min_length=2, max_length=64)
    name: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    method_type: str = "delivery"
    is_enabled: bool = True
    sort_order: int = 0
    estimate_min_days: Optional[int] = Field(default=None, ge=0, le=365)
    estimate_max_days: Optional[int] = Field(default=None, ge=0, le=365)


class StorefrontShippingMethodCreate(StorefrontShippingMethodBase):
    pass


class StorefrontShippingMethodUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=2, max_length=64)
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    method_type: Optional[str] = None
    is_enabled: Optional[bool] = None
    sort_order: Optional[int] = None
    estimate_min_days: Optional[int] = Field(default=None, ge=0, le=365)
    estimate_max_days: Optional[int] = Field(default=None, ge=0, le=365)


class StorefrontShippingMethod(StorefrontShippingMethodBase):
    id: UUID
    company_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class StorefrontShippingRuleBase(BaseModel):
    storefront_id: UUID
    method_id: UUID
    name: str = Field(..., min_length=2, max_length=120)
    priority: int = Field(default=100, ge=0, le=100000)
    is_enabled: bool = True
    destination_type: str = "global"
    country_code: Optional[str] = None
    state_code: Optional[str] = None
    state_name: Optional[str] = None
    city_code: Optional[str] = None
    city_name: Optional[str] = None
    payment_provider: Optional[str] = None
    min_subtotal: Optional[float] = Field(default=None, ge=0)
    max_subtotal: Optional[float] = Field(default=None, ge=0)
    min_weight: Optional[float] = Field(default=None, ge=0)
    max_weight: Optional[float] = Field(default=None, ge=0)
    charge_type: str = "flat"
    amount: float = Field(default=0, ge=0)
    rate_per_kg: float = Field(default=0, ge=0)
    estimate_min_days: Optional[int] = Field(default=None, ge=0, le=365)
    estimate_max_days: Optional[int] = Field(default=None, ge=0, le=365)


class StorefrontShippingRuleCreate(StorefrontShippingRuleBase):
    pass


class StorefrontShippingRuleUpdate(BaseModel):
    method_id: Optional[UUID] = None
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    priority: Optional[int] = Field(default=None, ge=0, le=100000)
    is_enabled: Optional[bool] = None
    destination_type: Optional[str] = None
    country_code: Optional[str] = None
    state_code: Optional[str] = None
    state_name: Optional[str] = None
    city_code: Optional[str] = None
    city_name: Optional[str] = None
    payment_provider: Optional[str] = None
    min_subtotal: Optional[float] = Field(default=None, ge=0)
    max_subtotal: Optional[float] = Field(default=None, ge=0)
    min_weight: Optional[float] = Field(default=None, ge=0)
    max_weight: Optional[float] = Field(default=None, ge=0)
    charge_type: Optional[str] = None
    amount: Optional[float] = Field(default=None, ge=0)
    rate_per_kg: Optional[float] = Field(default=None, ge=0)
    estimate_min_days: Optional[int] = Field(default=None, ge=0, le=365)
    estimate_max_days: Optional[int] = Field(default=None, ge=0, le=365)


class StorefrontShippingRule(StorefrontShippingRuleBase):
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
    theme_document: dict = Field(default_factory=dict)
    theme_documents: dict[str, dict] = Field(default_factory=dict)
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


class PublicTrackingConsent(BaseModel):
    analytics: bool = False
    marketing: bool = False


class PublicTrackingIntegration(BaseModel):
    provider: str
    app_slug: str
    tracking_id: str
    enabled: bool = True
    track_ecommerce: bool = True
    server_side_enabled: bool = False
    consent_category: str


PublicTrackingEventName = Literal[
    "page_view",
    "view_item",
    "search",
    "add_to_cart",
    "remove_from_cart",
    "view_cart",
    "begin_checkout",
    "add_shipping_info",
    "add_payment_info",
]


class PublicTrackingEventItem(BaseModel):
    item_id: str = Field(..., min_length=1, max_length=200)
    item_name: str = Field(default="Producto", min_length=1, max_length=240)
    price: float = Field(default=0, ge=0, le=100_000_000)
    quantity: float = Field(default=1, gt=0, le=10_000)
    item_variant: Optional[str] = Field(default=None, max_length=200)
    item_category: Optional[str] = Field(default=None, max_length=200)
    item_brand: Optional[str] = Field(default=None, max_length=200)


class PublicTrackingEventRequest(BaseModel):
    name: PublicTrackingEventName
    event_id: str = Field(..., min_length=8, max_length=255)
    client_id: Optional[str] = Field(default=None, min_length=8, max_length=255)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=12)
    value: Optional[float] = Field(default=None, ge=0, le=100_000_000)
    transaction_id: Optional[str] = Field(default=None, max_length=255)
    search_term: Optional[str] = Field(default=None, max_length=240)
    page_location: Optional[str] = Field(default=None, max_length=2048)
    items: list[PublicTrackingEventItem] = Field(default_factory=list, max_length=100)
    consent: PublicTrackingConsent = Field(default_factory=PublicTrackingConsent)


class PublicTrackingEventResponse(BaseModel):
    accepted: bool


class PublicProductVariant(BaseModel):
    id: UUID
    name: str
    sku: Optional[str] = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    price: float
    compare_at_price: Optional[float] = None
    in_stock: bool = True
    stock_quantity: Optional[float] = None


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
    variants: list[PublicProductVariant] = Field(default_factory=list)
    image_url: Optional[str] = None
    gallery: list[str] = Field(default_factory=list)
    price: float
    base_price: float
    compare_at_price: Optional[float] = None
    is_featured: bool = False
    show_stock: bool = True
    in_stock: bool = True
    stock_quantity: Optional[float] = None
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
    collections: list[PublicCatalogCategory] = Field(default_factory=list)
    brands: list[PublicCatalogFacet] = Field(default_factory=list)
    product_types: list[PublicCatalogProductType] = Field(default_factory=list)
    sizes: list[PublicCatalogFacet] = Field(default_factory=list)
    colors: list[PublicCatalogFacet] = Field(default_factory=list)
    total_products: int = 0
    min_price: float = 0
    max_price: float = 0
    current_page: int = 1
    page_size: int = 12
    total_pages: int = 1
    selected_collection_name: Optional[str] = None


class PublicCheckoutItemInput(BaseModel):
    published_product_id: UUID
    variant_id: Optional[UUID] = None
    quantity: float = 1


class PublicCheckoutCustomer(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=160)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=40)
    document_id: Optional[str] = Field(default=None, max_length=60)


class PublicCheckoutAddress(BaseModel):
    line1: str = Field(..., min_length=4, max_length=240)
    city: Optional[str] = Field(default=None, max_length=120)
    state: Optional[str] = Field(default=None, max_length=120)
    country: Optional[str] = Field(default=None, max_length=120)
    postal_code: Optional[str] = Field(default=None, max_length=40)
    state_code: Optional[str] = Field(default=None, max_length=32)
    city_code: Optional[str] = Field(default=None, max_length=32)


class PublicCheckoutPreviewRequest(BaseModel):
    items: list[PublicCheckoutItemInput] = Field(default_factory=list)
    shipping_amount: float = 0
    discount_amount: float = 0
    coupon_code: Optional[str] = None
    address: Optional[PublicCheckoutAddress] = None
    payment_provider: Optional[str] = None
    shipping_method_id: Optional[UUID] = None


class PublicCheckoutPreviewItem(BaseModel):
    published_product_id: UUID
    product_id: UUID
    variant_id: Optional[UUID] = None
    slug: str
    title: str
    variant_name: Optional[str] = None
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
    total_weight: float = 0
    shipping_method_id: Optional[UUID] = None
    shipping_method_name: Optional[str] = None
    shipping_rule_name: Optional[str] = None
    shipping_quote_required: bool = False
    shipping_requires_destination: bool = False


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
    shipping_method_id: Optional[UUID] = None
    tracking_consent: PublicTrackingConsent = Field(default_factory=PublicTrackingConsent)


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
    shipping_method_id: Optional[UUID] = None
    shipping_method_name: Optional[str] = None
    shipping_quote_required: bool = False


class PublicShippingDestination(BaseModel):
    id: UUID
    country_code: str
    state_code: Optional[str] = None
    state_name: str
    city_code: Optional[str] = None
    city_name: Optional[str] = None
    destination_type: str

    class Config:
        from_attributes = True


class PublicShippingMethod(BaseModel):
    id: UUID
    code: str
    name: str
    description: Optional[str] = None
    method_type: str
    sort_order: int = 0
    estimate_min_days: Optional[int] = None
    estimate_max_days: Optional[int] = None

    class Config:
        from_attributes = True


class PublicShippingConfig(BaseModel):
    destinations: list[PublicShippingDestination] = Field(default_factory=list)
    methods: list[PublicShippingMethod] = Field(default_factory=list)


class PublicPaymentIntentRequest(BaseModel):
    provider: str
    # The server derives amount and currency from this order. They stay optional
    # only to avoid breaking older storefront clients while they upgrade.
    amount: Optional[float] = None
    currency: Optional[str] = None
    order_id: UUID
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
    shipping_line1: Optional[str] = None
    shipping_city: Optional[str] = None
    shipping_state: Optional[str] = None
    shipping_country: Optional[str] = None
    shipping_postal_code: Optional[str] = None
