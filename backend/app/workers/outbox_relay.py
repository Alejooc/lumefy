"""Publish committed outbox events to Redis Streams with at-least-once delivery."""
import asyncio
import json
import os
from datetime import datetime

from redis import asyncio as redis
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.outbox_event import OutboxEvent

STREAM = os.getenv("REDIS_OUTBOX_STREAM", "lumefy:events")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
POLL_SECONDS = float(os.getenv("OUTBOX_POLL_SECONDS", "1"))


async def publish_pending_events(client: redis.Redis) -> int:
    async with SessionLocal() as db:
        result = await db.execute(
            select(OutboxEvent)
            .where(OutboxEvent.status.in_(["PENDING", "RETRY"]), OutboxEvent.available_at <= datetime.utcnow())
            .order_by(OutboxEvent.created_at)
            .limit(50)
            .with_for_update(skip_locked=True)
        )
        events = result.scalars().all()
        for event in events:
            try:
                await client.xadd(STREAM, {
                    "event_id": str(event.id),
                    "event_type": event.event_type,
                    "aggregate_type": event.aggregate_type,
                    "aggregate_id": str(event.aggregate_id),
                    "company_id": str(event.company_id),
                    "payload": json.dumps(event.payload),
                })
                event.status = "PUBLISHED"
                event.attempts += 1
                event.published_at = datetime.utcnow()
                event.last_error = None
            except Exception as exc:
                event.status = "RETRY"
                event.attempts += 1
                event.last_error = str(exc)[:2000]
        await db.commit()
        return len(events)


async def main() -> None:
    client = redis.from_url(REDIS_URL, decode_responses=True)
    try:
        while True:
            await publish_pending_events(client)
            await asyncio.sleep(POLL_SECONDS)
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
