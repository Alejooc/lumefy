import uuid

from sqlalchemy import ForeignKeyConstraint, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class StorefrontMediaAsset(BaseModel):
    """Tenant-scoped image uploaded for a storefront theme or branding."""

    __tablename__ = "storefront_media_assets"

    storefront_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)

    storefront = relationship("Storefront", back_populates="media_assets")

    __table_args__ = (
        UniqueConstraint(
            "storefront_id",
            "storage_path",
            name="uq_storefront_media_asset_storage_path",
        ),
        ForeignKeyConstraint(
            ["storefront_id", "company_id"],
            ["storefronts.id", "storefronts.company_id"],
            name="fk_storefront_media_asset_storefront_tenant",
            ondelete="CASCADE",
        ),
    )
