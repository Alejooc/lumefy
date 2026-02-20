from sqlalchemy import String, Float, ForeignKey, DateTime, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid
import enum
from datetime import datetime
from app.models.user import User
from app.models.branch import Branch
from app.models.product import Product
from app.models.client import Client

class SaleStatus(str, enum.Enum):
    QUOTE = "QUOTE"
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED" # Order confirmed, stock reserved
    PICKING = "PICKING" # Warehouse preparing
    PACKING = "PACKING" # Packed for shipment
    DISPATCHED = "DISPATCHED" # Shipped
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED" # Paid and done
    CANCELLED = "CANCELLED"

class Sale(BaseModel):
    __tablename__ = "sales"

    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    
    status: Mapped[SaleStatus] = mapped_column(Enum(SaleStatus), default=SaleStatus.DRAFT)
    
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    tax: Mapped[float] = mapped_column(Float, default=0.0)
    discount: Mapped[float] = mapped_column(Float, default=0.0)
    shipping_cost: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    
    payment_method: Mapped[str] = mapped_column(String, nullable=True) # CASH, CARD, MIXED
    
    # B2B Fields
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True) # For Quotes
    shipping_address: Mapped[str] = mapped_column(String, nullable=True)
    notes: Mapped[str] = mapped_column(String, nullable=True)
    
    # Delivery Fields
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_notes: Mapped[str] = mapped_column(String, nullable=True)
    delivery_evidence_url: Mapped[str] = mapped_column(String, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    branch = relationship(Branch)
    user = relationship(User)
    client = relationship("Client")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="sale", cascade="all, delete-orphan")

class SaleItem(BaseModel):
    __tablename__ = "sale_items"

    sale_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales.id"), index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))
    
    quantity: Mapped[float] = mapped_column(Float)
    quantity_picked: Mapped[float] = mapped_column(Float, default=0.0) # Track picked amount
    price: Mapped[float] = mapped_column(Float) # Unit price at moment of sale
    discount: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float)
    
    # Relationships
    sale = relationship("Sale", back_populates="items")
    product = relationship(Product)

class Payment(BaseModel):
    __tablename__ = "payments"
    
    sale_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales.id"), index=True)
    method: Mapped[str] = mapped_column(String) # CASH, CARD, TRANSFER
    amount: Mapped[float] = mapped_column(Float)
    reference: Mapped[str] = mapped_column(String, nullable=True) # Transaction ID, Authorization code
    
    sale = relationship("Sale", back_populates="payments")
