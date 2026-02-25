from sqlalchemy import ForeignKey, Boolean, JSON, UniqueConstraint, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.core.database import Base


class CompanyAppInstall(Base):
    __tablename__ = "company_app_installs"
    __table_args__ = (
        UniqueConstraint("company_id", "app_id", name="uq_company_app_install"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    app_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("app_definitions.id"), nullable=False, index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    installed_version: Mapped[str] = mapped_column(nullable=False, default="1.0.0")
    granted_scopes: Mapped[list] = mapped_column(JSON, nullable=True, default=list)
    api_key_prefix: Mapped[str] = mapped_column(String, nullable=True)
    api_key_hash: Mapped[str] = mapped_column(String, nullable=True)
    oauth_client_id: Mapped[str] = mapped_column(String, nullable=True)
    oauth_client_secret_hash: Mapped[str] = mapped_column(String, nullable=True)
    webhook_secret: Mapped[str] = mapped_column(String, nullable=True)
    webhook_url: Mapped[str] = mapped_column(String, nullable=True)
    billing_status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    settings: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    installed_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    installed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
