from sqlalchemy import Float, ForeignKey, Integer, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid

class PriceListItem(BaseModel):
    __tablename__ = "pricelist_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    pricelist_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("price_lists.id"), index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), index=True)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    
    min_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    # A value is an explicit override.  When a list has a formula, rows without
    # an item use the formula and rows with an item use this fixed value.
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Relationships
    pricelist = relationship("PriceList", back_populates="items")
    product = relationship("Product")
    variant = relationship("ProductVariant")

    __table_args__ = (
        # PostgreSQL treats NULLs as distinct, so the API also performs an
        # explicit upsert for product-level rows. These indexes protect the
        # common variant case and document the intended identity.
        UniqueConstraint("pricelist_id", "product_id", "variant_id", name="uq_pricelist_item_variant"),
        Index("ix_pricelist_items_product_variant", "pricelist_id", "product_id", "variant_id"),
    )
