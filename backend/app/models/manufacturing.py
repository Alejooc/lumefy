import enum
import uuid
from sqlalchemy import Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

class ManufacturingStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    DONE = "DONE"
    CANCELLED = "CANCELLED"

class BillOfMaterials(BaseModel):
    __tablename__ = "bills_of_materials"
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), index=True)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    product = relationship("Product")
    lines = relationship("BillOfMaterialsLine", cascade="all, delete-orphan")

class BillOfMaterialsLine(BaseModel):
    __tablename__ = "bill_of_materials_lines"
    bom_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bills_of_materials.id"), index=True)
    component_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))
    quantity: Mapped[float] = mapped_column(Float)
    component = relationship("Product")

class ManufacturingOrder(BaseModel):
    __tablename__ = "manufacturing_orders"
    bom_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bills_of_materials.id"))
    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id"))
    quantity: Mapped[float] = mapped_column(Float)
    status: Mapped[ManufacturingStatus] = mapped_column(Enum(ManufacturingStatus), default=ManufacturingStatus.DRAFT)
    bom = relationship("BillOfMaterials")
