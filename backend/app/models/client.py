from sqlalchemy import String, ForeignKey, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid
from datetime import datetime
from typing import Optional

class Client(BaseModel):
    __tablename__ = "clients"

    name: Mapped[str] = mapped_column(String, index=True)
    tax_id: Mapped[str] = mapped_column(String, index=True, nullable=True) # RUC/DNI/NIT
    email: Mapped[str] = mapped_column(String, index=True, nullable=True)
    phone: Mapped[str] = mapped_column(String, nullable=True)
    address: Mapped[str] = mapped_column(String, nullable=True)
    
    # CRM Fields
    status: Mapped[str] = mapped_column(String, default="active") # active, inactive, prospective, at_risk
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    last_interaction_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Notes or internal comments
    notes: Mapped[str] = mapped_column(String, nullable=True)

    # Credit and Accounts Receivable
    credit_limit: Mapped[float] = mapped_column(default=0.0) # 0 means no credit
    current_balance: Mapped[float] = mapped_column(default=0.0) # Positive means client owes us money
    
    price_list_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("price_lists.id"), nullable=True)
    
    # Relationships
    price_list = relationship("PriceList")
    ledger_entries = relationship("AccountLedger", primaryjoin="and_(AccountLedger.partner_id==Client.id, AccountLedger.partner_type=='CLIENT')", foreign_keys="[AccountLedger.partner_id]", lazy="select", back_populates="client")
    activities = relationship("ClientActivity", back_populates="client", cascade="all, delete-orphan")
