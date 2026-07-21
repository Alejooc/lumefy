import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox_event import OutboxEvent


def enqueue_outbox_event(
    db: AsyncSession,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: dict[str, Any],
) -> OutboxEvent:
    """Add an idempotent event; caller commits it with its business transaction."""
    event = OutboxEvent(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        idempotency_key=f"{event_type}:{aggregate_id}",
        payload=payload,
        company_id=company_id,
    )
    db.add(event)
    return event
