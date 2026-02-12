from sqlalchemy import String, Float, Boolean, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid
import enum
from app.models.category import Category

class ProductType(str, enum.Enum):
    STORABLE = "STORABLE"       # Physical product tracked in inventory
    CONSUMABLE = "CONSUMABLE"   # Physical but not tracked
    SERVICE = "SERVICE"          # Non-physical

class Product(BaseModel):
    __tablename__ = "products"

    # Basic Info
    name: Mapped[str] = mapped_column(String, index=True)
    internal_reference: Mapped[str] = mapped_column(String, nullable=True)  # Internal code
    sku: Mapped[str] = mapped_column(String, index=True, nullable=True)
    barcode: Mapped[str] = mapped_column(String, index=True, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    image_url: Mapped[str] = mapped_column(String, nullable=True)
    product_type: Mapped[str] = mapped_column(String, default="STORABLE")  # STORABLE, CONSUMABLE, SERVICE

    # Pricing
    price: Mapped[float] = mapped_column(Float, default=0.0)   # Sale price
    cost: Mapped[float] = mapped_column(Float, default=0.0)    # Purchase cost
    tax_rate: Mapped[float] = mapped_column(Float, default=0.0)  # Tax percentage (e.g. 19.0 = 19%)

    # Physical
    weight: Mapped[float] = mapped_column(Float, nullable=True)   # Weight in kg
    volume: Mapped[float] = mapped_column(Float, nullable=True)   # Volume in liters

    # Inventory Config
    track_inventory: Mapped[bool] = mapped_column(Boolean, default=True)
    min_stock: Mapped[float] = mapped_column(Float, default=0.0)
    sale_ok: Mapped[bool] = mapped_column(Boolean, default=True)      # Can be sold
    purchase_ok: Mapped[bool] = mapped_column(Boolean, default=True)   # Can be purchased

    # Foreign Keys
    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=True)
    unit_of_measure_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("units_of_measure.id"), nullable=True)
    purchase_uom_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("units_of_measure.id"), nullable=True)

    # Relationships
    category = relationship(Category, back_populates="products")
    brand = relationship("Brand", foreign_keys=[brand_id])
    unit_of_measure = relationship("UnitOfMeasure", foreign_keys=[unit_of_measure_id])
    purchase_uom = relationship("UnitOfMeasure", foreign_keys=[purchase_uom_id])
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
