from sqlalchemy import String, Float, ForeignKey, DateTime, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid
import enum

class LedgerType(str, enum.Enum):
    CHARGE = "CHARGE"      # Creates or increases debt (e.g., Credit Sale)
    PAYMENT = "PAYMENT"    # Reduces debt (e.g., Payment received)
    REFUND = "REFUND"      # Reverses a charge / increases balance to customer
    ADJUSTMENT = "ADJUSTMENT"

class PartnerType(str, enum.Enum):
    CLIENT = "CLIENT"
    SUPPLIER = "SUPPLIER"

class AccountLedger(BaseModel):
    __tablename__ = "account_ledger"

    # Polymorphic partner link
    partner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    partner_type: Mapped[PartnerType] = mapped_column(Enum(PartnerType))
    
    # Ledger details
    type: Mapped[LedgerType] = mapped_column(Enum(LedgerType))
    amount: Mapped[float] = mapped_column(Float) # Always positive
    balance_after: Mapped[float] = mapped_column(Float) # Snapshot of balance after this tx
    
    # Metadata
    reference_id: Mapped[str] = mapped_column(String, nullable=True, index=True) # E.g., Sale ID or Purchase ID
    description: Mapped[str] = mapped_column(Text)
    
    # Relationships
    client = relationship("Client", primaryjoin="and_(AccountLedger.partner_id==Client.id, AccountLedger.partner_type=='CLIENT')", foreign_keys="[AccountLedger.partner_id]", viewonly=True, back_populates="ledger_entries")
    supplier = relationship("Supplier", primaryjoin="and_(AccountLedger.partner_id==Supplier.id, AccountLedger.partner_type=='SUPPLIER')", foreign_keys="[AccountLedger.partner_id]", viewonly=True, back_populates="ledger_entries")
