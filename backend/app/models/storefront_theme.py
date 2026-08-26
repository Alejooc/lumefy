import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, Integer, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class StorefrontThemeDocument(BaseModel):
    """Tenant-scoped draft and published configuration for one template."""

    __tablename__ = "storefront_theme_documents"

    storefront_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    template_key: Mapped[str] = mapped_column(String(80), nullable=False, default="home")
    draft_document: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    published_document: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    draft_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    published_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "storefront_id",
            "template_key",
            name="uq_storefront_theme_document_template",
        ),
        ForeignKeyConstraint(
            ["storefront_id", "company_id"],
            ["storefronts.id", "storefronts.company_id"],
            name="fk_storefront_theme_document_storefront_tenant",
            ondelete="CASCADE",
        ),
    )


class StorefrontThemeRevision(BaseModel):
    """Immutable snapshot used for preview recovery and rollback."""

    __tablename__ = "storefront_theme_revisions"

    theme_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storefront_theme_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storefront_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    template_key: Mapped[str] = mapped_column(String(80), nullable=False, default="home")
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    document: Mapped[dict] = mapped_column(JSON, nullable=False)
    operation: Mapped[str] = mapped_column(String(30), nullable=False, default="publish")

    __table_args__ = (
        UniqueConstraint(
            "theme_document_id",
            "version",
            name="uq_storefront_theme_revision_version",
        ),
        ForeignKeyConstraint(
            ["storefront_id", "company_id"],
            ["storefronts.id", "storefronts.company_id"],
            name="fk_storefront_theme_revision_storefront_tenant",
            ondelete="CASCADE",
        ),
    )
