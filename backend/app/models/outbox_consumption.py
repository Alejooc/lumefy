import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OutboxConsumption(Base):
    """Idempotency receipt for an outbox event handled by a named consumer."""
    __tablename__ = "outbox_consumptions"
    __table_args__ = (UniqueConstraint("event_id", "consumer", name="uq_outbox_consumption_event_consumer"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("outbox_events.id"), index=True)
    consumer: Mapped[str] = mapped_column(String, nullable=False, index=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
