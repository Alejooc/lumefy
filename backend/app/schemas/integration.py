from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class IntegrationSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    provider_key: str = "custom_rest"
    source_type: str = "REST"
    base_url: str = Field(min_length=1, max_length=500)
    auth_type: str = "bearer"
    credentials: dict[str, Any] = Field(default_factory=dict)
    configuration: dict[str, Any] = Field(default_factory=dict)


class IntegrationSourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    provider_key: str | None = None
    source_type: str | None = None
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    auth_type: str | None = None
    credentials: dict[str, Any] | None = None
    configuration: dict[str, Any] | None = None
    is_active: bool | None = None


class IntegrationSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID | None
    name: str
    provider_key: str
    source_type: str
    base_url: str
    auth_type: str
    credentials_configured: bool
    configuration: dict[str, Any] = Field(default_factory=dict)
    status: str
    is_active: bool
    last_tested_at: datetime | None
    last_synced_at: datetime | None
    last_catalog_synced_at: datetime | None
    last_inventory_synced_at: datetime | None
    last_sync_status: str | None
    last_error: str | None
    inventory_sync_mode: str
    inventory_sync_interval_minutes: int | None
    next_inventory_sync_at: datetime | None
    created_at: datetime
    updated_at: datetime


class IntegrationTestOut(BaseModel):
    success: bool
    status_code: int | None = None
    message: str
    sample_count: int = 0


class IntegrationPreviewEntityOut(BaseModel):
    available: bool = True
    request_url: str | None = None
    status_code: int | None = None
    pagination_enabled: bool = False
    pagination_type: str | None = None
    page: int | None = None
    page_size: int | None = None
    received_count: int = 0
    mapped: list[dict[str, Any]] = Field(default_factory=list)
    raw: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
    variants_count: int = 0
    images_count: int = 0
    attributes_count: int = 0


class IntegrationPreviewOut(BaseModel):
    success: bool
    source_id: UUID
    message: str
    products: IntegrationPreviewEntityOut
    inventory: IntegrationPreviewEntityOut | None = None
    errors: list[str] = Field(default_factory=list)


class IntegrationPreflightOut(BaseModel):
    """Read-only compatibility report shown before an expensive sync."""

    source_id: UUID
    success: bool
    message: str
    checks: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    catalog: dict[str, Any] = Field(default_factory=dict)
    inventory: dict[str, Any] = Field(default_factory=dict)


class IntegrationMappingSuggestionOut(BaseModel):
    canonical: str
    source_path: str | None = None
    confidence: int = 0
    required: bool = False
    kind: str = "scalar"
    reason: str | None = None
    candidates: list[str] = Field(default_factory=list)


class IntegrationMappingOut(BaseModel):
    source_id: UUID
    success: bool
    message: str
    request_url: str | None = None
    sample_count: int = 0
    catalog_mode: str = "auto"
    detected_shape: str = "unknown"
    mapping: dict[str, Any] = Field(default_factory=dict)
    collections: dict[str, Any] = Field(default_factory=dict)
    suggestions: list[IntegrationMappingSuggestionOut] = Field(default_factory=list)
    detected_paths: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class IntegrationMappingConfirm(BaseModel):
    mapping: dict[str, Any] = Field(default_factory=dict)
    catalog_mode: str = "auto"
    collections: dict[str, Any] = Field(default_factory=dict)


class IntegrationInventoryScheduleUpdate(BaseModel):
    mode: Literal["MANUAL", "AUTOMATIC"] = "MANUAL"
    interval_minutes: int | None = Field(default=None, ge=5, le=1440)

    @model_validator(mode="after")
    def validate_automatic_interval(self) -> "IntegrationInventoryScheduleUpdate":
        if self.mode == "AUTOMATIC" and self.interval_minutes is None:
            raise ValueError("El intervalo es obligatorio para la sincronización automática.")
        if self.mode == "MANUAL":
            self.interval_minutes = None
        return self


class IntegrationSyncRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    sync_type: str
    trigger_type: str
    status: str
    queued_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    products_processed: int
    products_created: int
    products_updated: int
    inventory_processed: int
    inventory_updated: int
    items_failed: int
    details: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None
    created_at: datetime


class IntegrationWebhookOut(BaseModel):
    accepted: bool
    duplicate: bool = False
    status: str
    event_id: str | None = None
    event_type: str
    sync_type: str | None = None
    sync_run_id: UUID | None = None
