from datetime import datetime
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AppWebhookDelivery(Base):
    __tablename__ = "app_webhook_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    app_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("app_definitions.id"), nullable=False, index=True)
    install_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company_app_installs.id"), nullable=False, index=True
    )
    event_name: Mapped[str] = mapped_column(String, nullable=False)
    endpoint: Mapped[str] = mapped_column(String, nullable=True)
    request_payload: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    signature: Mapped[str] = mapped_column(String, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
