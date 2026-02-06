from sqlalchemy import String, Float, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid
from app.models.product import Product
from app.models.branch import Branch

class Inventory(BaseModel):
    __tablename__ = "inventory"

    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), index=True)
    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id"), index=True)
    
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Optional location tracking
    location: Mapped[str] = mapped_column(String, nullable=True)
    
    # Batch tracking (simplified for now)
    batch_number: Mapped[str] = mapped_column(String, nullable=True)
    expiry_date: Mapped[Date] = mapped_column(Date, nullable=True)

    # Relationships
    product = relationship(Product)
    branch = relationship(Branch)
