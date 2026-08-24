from sqlalchemy import String, Boolean, Enum, Float, ForeignKey
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

    # A sale list can be generated from the latest value received from one
    # integration source.  Purchase lists keep working without a source.
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integration_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    pricing_mode: Mapped[str] = mapped_column(String(30), default="FIXED")
    base_source: Mapped[str] = mapped_column(String(30), default="INTERNAL_PRICE")
    adjustment_value: Mapped[float] = mapped_column(Float, default=0.0)
    rounding_step: Mapped[float] = mapped_column(Float, default=0.0)
    min_margin_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Relationships
    items = relationship("PriceListItem", back_populates="pricelist", cascade="all, delete-orphan")
    source_rules = relationship("PriceListSourceRule", back_populates="pricelist", cascade="all, delete-orphan")
    source = relationship("IntegrationSource")
