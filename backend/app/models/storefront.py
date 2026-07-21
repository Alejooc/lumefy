from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Storefront(BaseModel):
    __tablename__ = "storefronts"

    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, index=True, nullable=False)
    subdomain: Mapped[str] = mapped_column(String, index=True, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    theme_key: Mapped[str] = mapped_column(String, default="modern")
    theme_settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    checkout_settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    seo_settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    currency: Mapped[str] = mapped_column(String, default="USD")
    language: Mapped[str] = mapped_column(String, default="es")
    fulfillment_warehouse_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=True, index=True)

    domains = relationship("StorefrontDomain", back_populates="storefront", cascade="all, delete-orphan")
    collections = relationship("StoreCollection", back_populates="storefront", cascade="all, delete-orphan")
    published_products = relationship("PublishedProduct", back_populates="storefront", cascade="all, delete-orphan")
    navigation_items = relationship("StoreNavigationItem", back_populates="storefront", cascade="all, delete-orphan")
    payment_gateways = relationship("StorePaymentGateway", back_populates="storefront", cascade="all, delete-orphan")
    orders = relationship("StorefrontOrder", back_populates="storefront", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("company_id", "slug", name="uq_storefront_company_slug"),
        UniqueConstraint("subdomain", name="uq_storefront_subdomain"),
    )


class StorefrontDomain(BaseModel):
    __tablename__ = "storefront_domains"

    storefront_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("storefronts.id"), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String, nullable=False, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_token: Mapped[str] = mapped_column(String, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    storefront = relationship("Storefront", back_populates="domains")

    __table_args__ = (
        UniqueConstraint("domain", name="uq_storefront_domain_domain"),
    )


class StoreCollection(BaseModel):
    __tablename__ = "store_collections"

    storefront_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("storefronts.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    image_url: Mapped[str] = mapped_column(String, nullable=True)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    storefront = relationship("Storefront", back_populates="collections")
    collection_products = relationship("StoreCollectionProduct", back_populates="collection", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("storefront_id", "slug", name="uq_store_collection_storefront_slug"),
    )


class PublishedProduct(BaseModel):
    __tablename__ = "published_products"

    storefront_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("storefronts.id"), nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    custom_title: Mapped[str] = mapped_column(String, nullable=True)
    custom_description: Mapped[str] = mapped_column(Text, nullable=True)
    slug: Mapped[str] = mapped_column(String, nullable=False, index=True)
    price_override: Mapped[float] = mapped_column(Float, nullable=True)
    compare_at_price: Mapped[float] = mapped_column(Float, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    show_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    seo_title: Mapped[str] = mapped_column(String, nullable=True)
    seo_description: Mapped[str] = mapped_column(Text, nullable=True)

    storefront = relationship("Storefront", back_populates="published_products")
    product = relationship("Product")
    collections = relationship("StoreCollectionProduct", back_populates="published_product", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("storefront_id", "product_id", name="uq_published_product_storefront_product"),
        UniqueConstraint("storefront_id", "slug", name="uq_published_product_storefront_slug"),
    )


class StoreCollectionProduct(BaseModel):
    __tablename__ = "store_collection_products"

    collection_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("store_collections.id"), nullable=False, index=True)
    published_product_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("published_products.id"), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    collection = relationship("StoreCollection", back_populates="collection_products")
    published_product = relationship("PublishedProduct", back_populates="collections")

    __table_args__ = (
        UniqueConstraint("collection_id", "published_product_id", name="uq_store_collection_product_pair"),
    )


class StoreNavigationItem(BaseModel):
    __tablename__ = "store_navigation_items"

    storefront_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("storefronts.id"), nullable=False, index=True)
    parent_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("store_navigation_items.id"), nullable=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
    item_type: Mapped[str] = mapped_column(String, nullable=False, default="collection")
    reference_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    url: Mapped[str] = mapped_column(String, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)

    storefront = relationship("Storefront", back_populates="navigation_items")
    parent = relationship("StoreNavigationItem", remote_side="StoreNavigationItem.id")


class StorePaymentGateway(BaseModel):
    __tablename__ = "store_payment_gateways"

    storefront_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("storefronts.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_sandbox: Mapped[bool] = mapped_column(Boolean, default=True)
    public_key: Mapped[str] = mapped_column(String, nullable=True)
    secret_key_encrypted: Mapped[str] = mapped_column(String, nullable=True)
    merchant_id: Mapped[str] = mapped_column(String, nullable=True)
    extra_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    storefront = relationship("Storefront", back_populates="payment_gateways")

    __table_args__ = (
        UniqueConstraint("storefront_id", "provider", name="uq_store_payment_gateway_storefront_provider"),
    )


class StorefrontOrder(BaseModel):
    __tablename__ = "storefront_orders"

    storefront_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("storefronts.id"), nullable=False, index=True)
    sale_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales.id"), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String, nullable=True, index=True)
    customer_user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    customer_name: Mapped[str] = mapped_column(String, nullable=False)
    customer_email: Mapped[str] = mapped_column(String, nullable=False, index=True)
    customer_phone: Mapped[str] = mapped_column(String, nullable=True)
    customer_document_id: Mapped[str] = mapped_column(String, nullable=True)
    shipping_line1: Mapped[str] = mapped_column(String, nullable=False)
    shipping_city: Mapped[str] = mapped_column(String, nullable=True)
    shipping_state: Mapped[str] = mapped_column(String, nullable=True)
    shipping_country: Mapped[str] = mapped_column(String, nullable=True)
    shipping_postal_code: Mapped[str] = mapped_column(String, nullable=True)
    coupon_code: Mapped[str] = mapped_column(String, nullable=True)
    buyer_note: Mapped[str] = mapped_column(Text, nullable=True)
    payment_provider: Mapped[str] = mapped_column(String, nullable=False)
    payment_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    currency: Mapped[str] = mapped_column(String, nullable=False, default="USD")
    fulfillment_warehouse_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=True, index=True)

    storefront = relationship("Storefront", back_populates="orders")
    sale = relationship("Sale", back_populates="storefront_order")
    customer_user = relationship("User")

    __table_args__ = (
        UniqueConstraint("sale_id", name="uq_storefront_order_sale"),
        UniqueConstraint("storefront_id", "idempotency_key", name="uq_storefront_order_storefront_idempotency"),
    )
