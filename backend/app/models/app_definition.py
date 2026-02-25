from sqlalchemy import String, Boolean, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.core.database import Base


class AppDefinition(Base):
    __tablename__ = "app_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=True, default="General")
    version: Mapped[str] = mapped_column(String, nullable=False, default="1.0.0")
    icon: Mapped[str] = mapped_column(String, nullable=True)
    requested_scopes: Mapped[list] = mapped_column(JSON, nullable=True, default=list)
    capabilities: Mapped[list] = mapped_column(JSON, nullable=True, default=list)
    config_schema: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    default_config: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    setup_url: Mapped[str] = mapped_column(String, nullable=True)
    docs_url: Mapped[str] = mapped_column(String, nullable=True)
    support_url: Mapped[str] = mapped_column(String, nullable=True)
    pricing_model: Mapped[str] = mapped_column(String, nullable=False, default="free")
    monthly_price: Mapped[float] = mapped_column(Float, nullable=True, default=0)
    is_listed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
