from sqlalchemy import String, Float, ForeignKey, DateTime, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid
import enum
from datetime import datetime


class ReturnStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ReturnType(str, enum.Enum):
    PARTIAL = "PARTIAL"
    TOTAL = "TOTAL"


class ReturnOrder(BaseModel):
    __tablename__ = "return_orders"

    sale_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales.id"), index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    return_type: Mapped[ReturnType] = mapped_column(Enum(ReturnType), default=ReturnType.PARTIAL)
    status: Mapped[ReturnStatus] = mapped_column(Enum(ReturnStatus), default=ReturnStatus.PENDING)
    reason: Mapped[str] = mapped_column(Text, nullable=True)
    total_refund: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    sale = relationship("Sale", backref="returns")
    creator = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])
    items = relationship("ReturnOrderItem", back_populates="return_order", cascade="all, delete-orphan")


class ReturnOrderItem(BaseModel):
    __tablename__ = "return_order_items"

    return_order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("return_orders.id"), index=True)
    sale_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sale_items.id"))
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))
    
    quantity_returned: Mapped[float] = mapped_column(Float)
    unit_price: Mapped[float] = mapped_column(Float)  # Price at time of sale
    subtotal: Mapped[float] = mapped_column(Float)

    # Relationships
    return_order = relationship("ReturnOrder", back_populates="items")
    sale_item = relationship("SaleItem")
    product = relationship("Product")
