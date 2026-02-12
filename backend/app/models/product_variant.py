from sqlalchemy import String, Float, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid

class ProductVariant(BaseModel):
    __tablename__ = "product_variants"

    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), index=True)
    name: Mapped[str] = mapped_column(String, index=True)  # e.g. "Rojo / XL", "500ml"
    sku: Mapped[str] = mapped_column(String, index=True, nullable=True)
    barcode: Mapped[str] = mapped_column(String, index=True, nullable=True)
    price_extra: Mapped[float] = mapped_column(Float, default=0.0)  # Additional price over base
    cost_extra: Mapped[float] = mapped_column(Float, default=0.0)   # Additional cost over base
    weight: Mapped[float] = mapped_column(Float, nullable=True)  # Override weight if different

    # Relationship back to product
    product = relationship("Product", back_populates="variants")
