from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid

class Supplier(BaseModel):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    
    name: Mapped[str] = mapped_column(String, index=True)
    email: Mapped[str] = mapped_column(String, nullable=True)
    phone: Mapped[str] = mapped_column(String, nullable=True)
    address: Mapped[str] = mapped_column(String, nullable=True)
    tax_id: Mapped[str] = mapped_column(String, nullable=True) # NIT/RUT/VAT
    
    # Credit and Accounts Payable
    credit_limit: Mapped[float] = mapped_column(default=0.0)
    current_balance: Mapped[float] = mapped_column(default=0.0) # Positive means we owe money to supplier
    
    price_list_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("price_lists.id"), nullable=True)

    # Relationships
    company = relationship("Company")
    price_list = relationship("PriceList")
    ledger_entries = relationship("AccountLedger", primaryjoin="and_(AccountLedger.partner_id==Supplier.id, AccountLedger.partner_type=='SUPPLIER')", foreign_keys="[AccountLedger.partner_id]", lazy="select", back_populates="supplier")
