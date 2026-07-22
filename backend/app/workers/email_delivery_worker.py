"""Retry durable customer email deliveries without replaying business effects."""
import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.email_delivery import EmailDelivery
from app.services.email import EmailService


async def deliver_pending() -> int:
    async with SessionLocal() as db:
        result = await db.execute(select(EmailDelivery).where(
            EmailDelivery.status.in_(["PENDING", "RETRY"]),
            EmailDelivery.available_at <= datetime.utcnow(),
        ).order_by(EmailDelivery.created_at).limit(25).with_for_update(skip_locked=True))
        deliveries = result.scalars().all()
        for delivery in deliveries:
            try:
                await EmailService.send_email(delivery.recipient, delivery.subject, delivery.html_content)
                delivery.status, delivery.sent_at, delivery.last_error = "SENT", datetime.utcnow(), None
            except Exception as exc:
                delivery.attempts += 1
                delivery.status = "RETRY"
                delivery.available_at = datetime.utcnow() + timedelta(minutes=min(30, 2 ** min(delivery.attempts, 5)))
                delivery.last_error = str(exc)[:2000]
            else:
                delivery.attempts += 1
        await db.commit()
        return len(deliveries)


async def main() -> None:
    while True:
        await deliver_pending()
        await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
