from sqlalchemy import String, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid
import enum

class PriceListType(str, enum.Enum):
    SALE = "SALE"
    PURCHASE = "PURCHASE"

class PriceList(BaseModel):
    __tablename__ = "price_lists"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, index=True)
    type: Mapped[PriceListType] = mapped_column(Enum(PriceListType), default=PriceListType.SALE)
    currency: Mapped[str] = mapped_column(String, default="USD")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    items = relationship("PriceListItem", back_populates="pricelist", cascade="all, delete-orphan")
