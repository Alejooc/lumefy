from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class StorefrontPromotion(BaseModel):
    """A Shopify-style promotion owned by one storefront.

    ``discount_percent`` is kept nullable for backwards compatibility with
    the first promotion migration. New records use ``discount_value`` as the
    canonical amount and keep the legacy field populated for percentage
    promotions so older API consumers continue to work.
    """

    __tablename__ = "storefront_promotions"

    storefront_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("storefronts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    collection_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("store_collections.id", ondelete="CASCADE"), nullable=True, index=True
    )
    published_product_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("published_products.id", ondelete="CASCADE"), nullable=True, index=True
    )
    promotion_type: Mapped[str] = mapped_column(String(24), nullable=False, default="AMOUNT_OFF")
    reward_target_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    reward_collection_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("store_collections.id", ondelete="CASCADE"), nullable=True, index=True
    )
    reward_published_product_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("published_products.id", ondelete="CASCADE"), nullable=True, index=True
    )
    buy_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    get_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    get_discount_type: Mapped[str] = mapped_column(String(16), nullable=False, default="PERCENT")
    get_discount_value: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    method: Mapped[str] = mapped_column(String(16), nullable=False, default="AUTOMATIC")
    code: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False, default="PERCENT")
    discount_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    discount_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    minimum_requirement: Mapped[str] = mapped_column(String(16), nullable=False, default="NONE")
    minimum_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    minimum_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    once_per_customer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    combines_with_product: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    combines_with_order: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    combines_with_shipping: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    customer_eligibility: Mapped[str] = mapped_column(String(24), nullable=False, default="ALL")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    storefront = relationship("Storefront")
    collection = relationship("StoreCollection", foreign_keys=[collection_id])
    published_product = relationship("PublishedProduct", foreign_keys=[published_product_id])
    reward_collection = relationship("StoreCollection", foreign_keys=[reward_collection_id])
    reward_published_product = relationship("PublishedProduct", foreign_keys=[reward_published_product_id])
