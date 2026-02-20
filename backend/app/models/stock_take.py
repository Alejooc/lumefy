from sqlalchemy import String, Float, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid
import enum
from app.models.branch import Branch
from app.models.user import User
from app.models.product import Product


class StockTakeStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class StockTake(BaseModel):
    __tablename__ = "stock_takes"

    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status: Mapped[StockTakeStatus] = mapped_column(Enum(StockTakeStatus), default=StockTakeStatus.IN_PROGRESS)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships
    branch = relationship(Branch)
    user = relationship(User)
    items = relationship("StockTakeItem", back_populates="stock_take", cascade="all, delete-orphan")


class StockTakeItem(BaseModel):
    __tablename__ = "stock_take_items"

    stock_take_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_takes.id"), index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), index=True)
    
    system_qty: Mapped[float] = mapped_column(Float, default=0.0)
    counted_qty: Mapped[float] = mapped_column(Float, nullable=True)
    difference: Mapped[float] = mapped_column(Float, default=0.0)

    # Relationships
    stock_take = relationship("StockTake", back_populates="items")
    product = relationship(Product)
