from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.encrypted_types import EncryptedGatewayConfig
from app.models.base import BaseModel


class IntegrationSource(BaseModel):
    """A company-owned external system that exchanges data with Lumefy."""

    __tablename__ = "integration_sources"

    name: Mapped[str] = mapped_column(String, nullable=False)
    provider_key: Mapped[str] = mapped_column(String(100), nullable=False, default="custom_rest")
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="REST")
    base_url: Mapped[str] = mapped_column(String, nullable=False)
    auth_type: Mapped[str] = mapped_column(String(50), nullable=False, default="bearer")
    credentials: Mapped[dict] = mapped_column(EncryptedGatewayConfig(), nullable=False, default=dict)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_catalog_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_inventory_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    inventory_sync_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="MANUAL")
    inventory_sync_interval_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_inventory_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    sync_runs = relationship(
        "IntegrationSyncRun",
        back_populates="source",
        cascade="all, delete-orphan",
        order_by="IntegrationSyncRun.created_at.desc()",
    )
    record_links = relationship(
        "IntegrationRecordLink",
        back_populates="source",
        cascade="all, delete-orphan",
    )


class IntegrationSyncRun(BaseModel):
    __tablename__ = "integration_sync_runs"
    __table_args__ = (
        Index(
            "uq_integration_sync_runs_active_type",
            "source_id",
            "sync_type",
            unique=True,
            postgresql_where=text("status IN ('QUEUED', 'RUNNING')"),
        ),
        Index(
            "uq_integration_sync_runs_running_source",
            "source_id",
            unique=True,
            postgresql_where=text("status = 'RUNNING'"),
        ),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integration_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    sync_type: Mapped[str] = mapped_column(String(20), nullable=False, default="FULL")
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False, default="MANUAL")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="QUEUED")
    queued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    products_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    products_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    products_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inventory_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inventory_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    source = relationship("IntegrationSource", back_populates="sync_runs")


class IntegrationRecordLink(BaseModel):
    """Stable mapping between an external record and a normalized Lumefy record."""

    __tablename__ = "integration_record_links"
    __table_args__ = (
        UniqueConstraint("source_id", "entity_type", "external_id", name="uq_integration_record_external"),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integration_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_sku: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    local_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    local_variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    source = relationship("IntegrationSource", back_populates="record_links")


class IntegrationWebhookEvent(BaseModel):
    """A verified provider event kept for idempotent webhook handling."""

    __tablename__ = "integration_webhook_events"
    __table_args__ = (
        UniqueConstraint("source_id", "event_key", name="uq_integration_webhook_source_event"),
        Index("ix_integration_webhook_events_received_at", "received_at"),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integration_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sync_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integration_sync_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_key: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, default="unknown")
    sync_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="QUEUED")
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    source = relationship("IntegrationSource")
    sync_run = relationship("IntegrationSyncRun")
