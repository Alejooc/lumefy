from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid

class Client(BaseModel):
    __tablename__ = "clients"

    name: Mapped[str] = mapped_column(String, index=True)
    tax_id: Mapped[str] = mapped_column(String, index=True, nullable=True) # RUC/DNI/NIT
    email: Mapped[str] = mapped_column(String, index=True, nullable=True)
    phone: Mapped[str] = mapped_column(String, nullable=True)
    address: Mapped[str] = mapped_column(String, nullable=True)
    
    # Notes or internal comments
    notes: Mapped[str] = mapped_column(String, nullable=True)

    price_list_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("price_lists.id"), nullable=True)
    
    # Relationships
    price_list = relationship("PriceList")
