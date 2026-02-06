from sqlalchemy import String, Float, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid
import enum
from app.models.product import Product
from app.models.branch import Branch
from app.models.user import User

class MovementType(str, enum.Enum):
    IN = "IN"   # Purchase or Return
    OUT = "OUT" # Sale or Damage
    ADJ = "ADJ" # Manual Adjustment
    TRF = "TRF" # Transfer between branches

class InventoryMovement(BaseModel):
    __tablename__ = "inventory_movements"

    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), index=True)
    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    type: Mapped[MovementType] = mapped_column(Enum(MovementType), index=True)
    quantity: Mapped[float] = mapped_column(Float) # Positive or Negative based on type logic, but usually stored roughly absolute here and logic handles sign? Or signed? Best strictly signed for sum() queries.
    # Actually, standard is: IN is +, OUT is -, ADJ is +/-.
    # We will store signed value in `quantity` for easy aggregation.

    previous_stock: Mapped[float] = mapped_column(Float, default=0.0)
    new_stock: Mapped[float] = mapped_column(Float, default=0.0)
    
    reference_id: Mapped[str] = mapped_column(String, nullable=True) # ID of Sale, Purchase, etc.
    reason: Mapped[str] = mapped_column(String, nullable=True) # "Expired", "Gift", "Correction"

    # Relationships
    product = relationship(Product)
    branch = relationship(Branch)
    user = relationship(User)
