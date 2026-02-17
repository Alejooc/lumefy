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
    installed: bool
    is_enabled: bool = False
    config_schema: Dict[str, Any] = Field(default_factory=dict)


class AppInstallOut(BaseModel):
    install_id: UUID
    app_id: UUID
    slug: str
    name: str
    is_enabled: bool
    settings: Dict[str, Any] = Field(default_factory=dict)
    installed_at: datetime


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
    config_schema: Dict[str, Any] = Field(default_factory=dict)
    default_config: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class AppDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    version: Optional[str] = None
    icon: Optional[str] = None
    config_schema: Optional[Dict[str, Any]] = None
    default_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class AppDefinitionOut(BaseModel):
    id: UUID
    slug: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    version: str
    icon: Optional[str] = None
    config_schema: Dict[str, Any] = Field(default_factory=dict)
    default_config: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool


class AppInstalledDetail(BaseModel):
    install_id: UUID
    app_id: UUID
    slug: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    version: str
    is_enabled: bool
    settings: Dict[str, Any] = Field(default_factory=dict)
    config_schema: Dict[str, Any] = Field(default_factory=dict)
    installed_at: datetime
