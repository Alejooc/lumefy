from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
# Import Branch to ensure visibility
from app.models.branch import Branch

class Company(BaseModel):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String, index=True)
    tax_id: Mapped[str] = mapped_column(String, nullable=True)  # RUC/NIT/VAT
    address: Mapped[str] = mapped_column(String, nullable=True)
    phone: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=True)
    website: Mapped[str] = mapped_column(String, nullable=True)
    currency: Mapped[str] = mapped_column(String, default="USD")
    currency_symbol: Mapped[str] = mapped_column(String, default="$")
    logo_url: Mapped[str] = mapped_column(String, nullable=True)

    # SaaS Fields
    plan: Mapped[str] = mapped_column(String, default="FREE") # FREE, PRO, ENTERPRISE
    valid_until: Mapped[str] = mapped_column(String, nullable=True) # ISO Date
    is_active: Mapped[bool] = mapped_column(default=True)
    
    # Relationships
    # Relationships
    # branches = relationship(Branch, back_populates="company")
    users = relationship("app.models.user.User", back_populates="company")
