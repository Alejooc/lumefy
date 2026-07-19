import uuid
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class InventoryLot(BaseModel):
    __tablename__ = "inventory_lots"

    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), index=True)
    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id"), index=True)
    lot_number: Mapped[str] = mapped_column(String, nullable=True, index=True)
    serial_number: Mapped[str] = mapped_column(String, nullable=True, index=True)
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=True)
    unit_cost: Mapped[float] = mapped_column(Float, default=0.0)
    source_reference: Mapped[str] = mapped_column(String, nullable=True)

    product = relationship("Product")
    branch = relationship("Branch")
