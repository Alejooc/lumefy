import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class FulfillmentTask(BaseModel):
    __tablename__ = "fulfillment_tasks"
    __table_args__ = (UniqueConstraint("sale_id", "task_type", name="uq_fulfillment_task_sale_type"),)

    sale_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales.id"), index=True)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=True, index=True)
    task_type: Mapped[str] = mapped_column(String, default="PICKING")
    status: Mapped[str] = mapped_column(String, default="OPEN", index=True)
    sale = relationship("Sale")
    warehouse = relationship("Warehouse")
