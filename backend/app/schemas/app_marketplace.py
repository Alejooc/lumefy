from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class AppCatalogItem(BaseModel):
    id: UUID
    slug: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    version: str
    icon: Optional[str] = None
    is_active: bool
    is_listed: bool = True
    requested_scopes: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    pricing_model: str = "free"
    monthly_price: float = 0
    setup_url: Optional[str] = None
    docs_url: Optional[str] = None
    support_url: Optional[str] = None
    installed: bool
    is_enabled: bool = False
    config_schema: Dict[str, Any] = Field(default_factory=dict)


class AppInstallOut(BaseModel):
    install_id: UUID
    app_id: UUID
    slug: str
    name: str
    is_enabled: bool
    installed_version: str
    granted_scopes: list[str] = Field(default_factory=list)
    api_key_prefix: Optional[str] = None
    oauth_client_id: Optional[str] = None
    webhook_url: Optional[str] = None
    billing_status: str = "active"
    new_api_key: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)
    installed_at: datetime


class AppInstallRequest(BaseModel):
    granted_scopes: list[str] = Field(default_factory=list)
    target_version: Optional[str] = None


class AppConfigUpdate(BaseModel):
    settings: Dict[str, Any]


class DemoAppResponse(BaseModel):
    app_slug: str
    message: str
    configured_message: str


class AppDefinitionCreate(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = "General"
    version: str = "1.0.0"
    icon: Optional[str] = None
    requested_scopes: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    config_schema: Dict[str, Any] = Field(default_factory=dict)
    default_config: Dict[str, Any] = Field(default_factory=dict)
    setup_url: Optional[str] = None
    docs_url: Optional[str] = None
    support_url: Optional[str] = None
    pricing_model: str = "free"
    monthly_price: float = 0
    is_listed: bool = True
    is_active: bool = True


class AppDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    version: Optional[str] = None
    icon: Optional[str] = None
    requested_scopes: Optional[list[str]] = None
    capabilities: Optional[list[str]] = None
    config_schema: Optional[Dict[str, Any]] = None
    default_config: Optional[Dict[str, Any]] = None
    setup_url: Optional[str] = None
    docs_url: Optional[str] = None
    support_url: Optional[str] = None
    pricing_model: Optional[str] = None
    monthly_price: Optional[float] = None
    is_listed: Optional[bool] = None
    is_active: Optional[bool] = None


class AppDefinitionOut(BaseModel):
    id: UUID
    slug: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    version: str
    icon: Optional[str] = None
    requested_scopes: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    config_schema: Dict[str, Any] = Field(default_factory=dict)
    default_config: Dict[str, Any] = Field(default_factory=dict)
    setup_url: Optional[str] = None
    docs_url: Optional[str] = None
    support_url: Optional[str] = None
    pricing_model: str = "free"
    monthly_price: float = 0
    is_listed: bool = True
    is_active: bool


class AppInstalledDetail(BaseModel):
    install_id: UUID
    app_id: UUID
    slug: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    version: str
    icon: Optional[str] = None
    is_enabled: bool
    installed_version: str
    granted_scopes: list[str] = Field(default_factory=list)
    api_key_prefix: Optional[str] = None
    oauth_client_id: Optional[str] = None
    webhook_url: Optional[str] = None
    billing_status: str = "active"
    settings: Dict[str, Any] = Field(default_factory=dict)
    config_schema: Dict[str, Any] = Field(default_factory=dict)
    default_config: Dict[str, Any] = Field(default_factory=dict)
    requested_scopes: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    setup_url: Optional[str] = None
    docs_url: Optional[str] = None
    support_url: Optional[str] = None
    pricing_model: str = "free"
    monthly_price: float = 0
    installed_at: datetime


class AppInstallEventOut(BaseModel):
    id: UUID
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    triggered_by_user_id: Optional[UUID] = None


class RotateApiKeyOut(BaseModel):
    api_key_prefix: str
    new_api_key: str
    rotated_at: datetime


class RotateWebhookSecretOut(BaseModel):
    webhook_secret: str
    rotated_at: datetime


class RotateClientSecretOut(BaseModel):
    oauth_client_id: str
    new_client_secret: str
    rotated_at: datetime


class AppBillingSummary(BaseModel):
    slug: str
    name: str
    pricing_model: str
    monthly_price: float
    currency: str = "USD"
    billing_status: str
    is_enabled: bool
    next_invoice_date: Optional[datetime] = None


class WebhookTestOut(BaseModel):
    delivered: bool
    endpoint: Optional[str] = None
    status_code: Optional[int] = None
    signature: Optional[str] = None
    reason: Optional[str] = None


class WebhookDeliveryOut(BaseModel):
    id: UUID
    event_name: str
    endpoint: Optional[str] = None
    success: bool
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    attempt_number: int
    created_at: datetime
