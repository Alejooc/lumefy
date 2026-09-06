from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class StorefrontPromotion(BaseModel):
    """A percentage discount applied to a storefront collection or product."""

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
    discount_percent: Mapped[float] = mapped_column(Float, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    storefront = relationship("Storefront")
    collection = relationship("StoreCollection")
    published_product = relationship("PublishedProduct")
