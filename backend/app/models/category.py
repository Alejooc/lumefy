from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid

class Category(BaseModel):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    parent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    
    # Relationships
    products = relationship("Product", back_populates="category")
    # children = relationship("Category") # Simplified for now to avoid circular dependency issues in async setup without careful config
