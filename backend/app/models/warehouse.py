import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Warehouse(BaseModel):
    """Physical fulfillment site inside a commercial branch."""

    __tablename__ = "warehouses"
    __table_args__ = (UniqueConstraint("branch_id", "code", name="uq_warehouse_branch_code"),)

    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id"), index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    allows_ecommerce: Mapped[bool] = mapped_column(Boolean, default=True)

    branch = relationship("Branch")
