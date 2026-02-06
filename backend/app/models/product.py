from sqlalchemy import String, Float, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid
from app.models.category import Category

class Product(BaseModel):
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String, index=True)
    sku: Mapped[str] = mapped_column(String, index=True, nullable=True)
    barcode: Mapped[str] = mapped_column(String, index=True, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    
    # Pricing
    price: Mapped[float] = mapped_column(Float, default=0.0)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Inventory Config
    track_inventory: Mapped[bool] = mapped_column(Boolean, default=True)
    min_stock: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Foreign Keys
    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    
    # Relationships
    # Relationships
    category = relationship(Category, back_populates="products")
