import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class OutboxEvent(BaseModel):
    """Durable event written in the same transaction as a business change."""

    __tablename__ = "outbox_events"

    event_type: Mapped[str] = mapped_column(String, index=True)
    aggregate_type: Mapped[str] = mapped_column(String, index=True)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    idempotency_key: Mapped[str] = mapped_column(String, unique=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String, default="PENDING", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str] = mapped_column(Text, nullable=True)
