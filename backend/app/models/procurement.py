import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class PurchaseRequestStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    CONVERTED = "CONVERTED"
    CANCELLED = "CANCELLED"


class SupplierQuoteStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class PurchaseRequest(BaseModel):
    __tablename__ = "purchase_requests"

    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False)
    requested_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=True)
    status: Mapped[PurchaseRequestStatus] = mapped_column(Enum(PurchaseRequestStatus), default=PurchaseRequestStatus.DRAFT, index=True)
    priority: Mapped[str] = mapped_column(String, default="NORMAL")
    requested_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    branch = relationship("Branch")
    requested_by = relationship("User")
    purchase_order = relationship("PurchaseOrder")
    items = relationship("PurchaseRequestItem", back_populates="request", cascade="all, delete-orphan")
    quotes = relationship("SupplierQuote", back_populates="request", cascade="all, delete-orphan")


class PurchaseRequestItem(BaseModel):
    __tablename__ = "purchase_request_items"

    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("purchase_requests.id"), index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)

    request = relationship("PurchaseRequest", back_populates="items")
    product = relationship("Product")


class SupplierQuote(BaseModel):
    __tablename__ = "supplier_quotes"

    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("purchase_requests.id"), index=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)
    status: Mapped[SupplierQuoteStatus] = mapped_column(Enum(SupplierQuoteStatus), default=SupplierQuoteStatus.DRAFT, index=True)
    reference_number: Mapped[str] = mapped_column(String, nullable=True)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    request = relationship("PurchaseRequest", back_populates="quotes")
    supplier = relationship("Supplier")
    items = relationship("SupplierQuoteItem", back_populates="quote", cascade="all, delete-orphan")


class SupplierQuoteItem(BaseModel):
    __tablename__ = "supplier_quote_items"

    quote_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("supplier_quotes.id"), index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)

    quote = relationship("SupplierQuote", back_populates="items")
    product = relationship("Product")
