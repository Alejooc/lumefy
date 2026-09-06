"""Release inventory held by genuinely expired storefront checkouts."""

import asyncio
import logging
import os
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.models.sale import Sale, SaleStatus
from app.models.storefront import StorefrontOrder
from app.services.storefront_payment_expiry import payment_pending_deadline


LOGGER = logging.getLogger("lumefy.storefront_order_expiry")
POLL_SECONDS = max(float(os.getenv("STOREFRONT_EXPIRY_POLL_SECONDS", "60")), 5.0)
BATCH_SIZE = max(int(os.getenv("STOREFRONT_EXPIRY_BATCH_SIZE", "100")), 1)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def expire_pending_storefront_orders(*, now: datetime | None = None, limit: int = BATCH_SIZE) -> int:
    """Expire only pending orders still eligible for cancellation.

    The row lock makes multiple worker replicas safe. Provider callbacks that
    arrive after this transaction see ``expired`` and cannot turn it into an
    approved order through the existing callback state machine.
    """
    current_time = _as_utc(now) or datetime.now(timezone.utc)
    expired_orders = []

    async with SessionLocal() as db:
        result = await db.execute(
            select(StorefrontOrder)
            .options(
                selectinload(StorefrontOrder.sale),
                selectinload(StorefrontOrder.storefront),
            )
            .join(Sale, Sale.id == StorefrontOrder.sale_id)
            .where(
                StorefrontOrder.is_active.is_(True),
                func.lower(StorefrontOrder.payment_status) == "pending",
                Sale.status.in_((SaleStatus.DRAFT, SaleStatus.QUOTE, SaleStatus.CONFIRMED)),
            )
            .order_by(StorefrontOrder.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        orders = result.scalars().unique().all()

        # Importing the endpoint here avoids coupling the application startup
        # router import to the worker while reusing the canonical reservation
        # release implementation and its audit/outbox effects.
        from app.api.v1.endpoints.storefront import _cancel_storefront_sale_and_release_reservation, _send_storefront_payment_status_email
        from app.core.audit import log_sale_event

        for order in orders:
            sale = order.sale
            if not sale:
                continue
            deadline = _as_utc(order.payment_pending_until)
            if deadline is None:
                deadline = payment_pending_deadline(order.payment_provider, created_at=_as_utc(order.created_at))
            if deadline > current_time:
                continue

            previous_status = (order.payment_status or "pending").lower()
            if not await _cancel_storefront_sale_and_release_reservation(db, sale):
                LOGGER.warning("Could not release reservation for expired storefront order %s", order.id)
                continue
            order.payment_status = "expired"
            await log_sale_event(
                db,
                sale_id=str(sale.id),
                company_id=str(sale.company_id),
                event_type="PAYMENT_STATUS_UPDATED",
                title="Pago pendiente vencido",
                description="El plazo de pago terminó y la reserva fue liberada.",
                status="warning",
                provider=order.payment_provider,
                metadata={"from": previous_status, "to": "expired", "source": "expiry_worker"},
            )
            db.add(order)
            expired_orders.append(order)

        await db.commit()

        # Email is best-effort and intentionally happens after the state and
        # inventory transaction is durable.
        for order in expired_orders:
            try:
                await _send_storefront_payment_status_email(order)
            except Exception:  # noqa: BLE001 - notification must not stop expiry
                LOGGER.exception("Could not notify expired storefront order %s", order.id)

    return len(expired_orders)


async def main() -> None:
    while True:
        try:
            await expire_pending_storefront_orders()
        except Exception:  # noqa: BLE001 - keep the worker alive and observable
            LOGGER.exception("Storefront expiry polling cycle failed")
        await asyncio.sleep(POLL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    asyncio.run(main())
