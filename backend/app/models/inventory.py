from sqlalchemy import Date, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid
from app.models.product import Product
from app.models.branch import Branch

class Inventory(BaseModel):
    __tablename__ = "inventory"
    __table_args__ = (
        Index(
            "uq_inventory_stock_identity",
            "company_id",
            "product_id",
            "branch_id",
            "warehouse_id",
            "variant_id",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), index=True)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id"), index=True)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=True, index=True)
    
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    reserved_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    average_cost: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Optional location tracking
    location: Mapped[str] = mapped_column(String, nullable=True)
    
    # Batch tracking (simplified for now)
    batch_number: Mapped[str] = mapped_column(String, nullable=True)
    expiry_date: Mapped[Date] = mapped_column(Date, nullable=True)

    # Relationships
    product = relationship(Product)
    variant = relationship("ProductVariant")
    branch = relationship(Branch)
    warehouse = relationship("Warehouse")
