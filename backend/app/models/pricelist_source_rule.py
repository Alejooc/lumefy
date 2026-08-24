from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class PriceListSourceRule(BaseModel):
    """A supplier/source-specific rule inside one sale price list."""

    __tablename__ = "pricelist_source_rules"
    __table_args__ = (
        UniqueConstraint("pricelist_id", "source_id", name="uq_pricelist_source_rule"),
        Index("ix_pricelist_source_rules_pricelist", "pricelist_id"),
    )

    pricelist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("price_lists.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integration_sources.id", ondelete="CASCADE"), nullable=False
    )
    pricing_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="MARKUP_PERCENT")
    base_source: Mapped[str] = mapped_column(String(30), nullable=False, default="EXTERNAL_PRICE")
    adjustment_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rounding_step: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    min_margin_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    pricelist = relationship("PriceList", back_populates="source_rules")
    source = relationship("IntegrationSource")
