from sqlalchemy import String, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid
from app.models.sale import Sale, SaleItem

class PackageType(BaseModel):
    __tablename__ = "package_types"

    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    width: Mapped[float] = mapped_column(Float, default=0.0)
    height: Mapped[float] = mapped_column(Float, default=0.0)
    length: Mapped[float] = mapped_column(Float, default=0.0)
    max_weight: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Relationships
    packages = relationship("SalePackage", back_populates="package_type")

class SalePackage(BaseModel):
    __tablename__ = "sale_packages"

    sale_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales.id"), index=True)
    package_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("package_types.id"), nullable=True)
    
    tracking_number: Mapped[str] = mapped_column(String, nullable=True)
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    shipping_label_url: Mapped[str] = mapped_column(String, nullable=True)
    
    # Relationships
    sale = relationship("Sale")
    package_type = relationship(PackageType, back_populates="packages")
    items = relationship("SalePackageItem", back_populates="package", cascade="all, delete-orphan")

class SalePackageItem(BaseModel):
    __tablename__ = "sale_package_items"

    package_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sale_packages.id"), index=True)
    sale_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sale_items.id"))
    
    quantity: Mapped[float] = mapped_column(Float)
    
    # Relationships
    package = relationship("SalePackage", back_populates="items")
    sale_item = relationship("SaleItem")
