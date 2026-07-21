"""Idempotent consumer for operational inventory events from Redis Streams."""
import asyncio
import json
import os
import socket
import uuid

from redis import asyncio as redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.models.fulfillment_task import FulfillmentTask
from app.models.notification import Notification
from app.models.outbox_consumption import OutboxConsumption
from app.models.sale import Sale
from app.models.storefront import StorefrontOrder
from app.services.email import EmailService

STREAM = os.getenv("REDIS_OUTBOX_STREAM", "lumefy:events")
GROUP = "operations"
CONSUMER = os.getenv("OUTBOX_CONSUMER_NAME", socket.gethostname())
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


async def process_event(event_id: str, event_type: str, payload: dict) -> bool:
    """Apply operational effects and persist the receipt in one transaction."""
    parsed_event_id = uuid.UUID(event_id)
    customer_email = None
    customer_name = None
    order_code = None
    customer_subject = None
    customer_body = None
    async with SessionLocal() as db:
        exists = await db.scalar(select(OutboxConsumption.id).where(
            OutboxConsumption.event_id == parsed_event_id,
            OutboxConsumption.consumer == GROUP,
        ))
        if exists:
            return True

        sale_id = payload.get("sale_id")
        sale = None
        if sale_id:
            try:
                sale = await db.get(Sale, uuid.UUID(str(sale_id)))
            except (TypeError, ValueError):
                raise ValueError("inventory event has an invalid sale_id")

        if event_type == "inventory.reserved" and sale:
            task = await db.scalar(select(FulfillmentTask).where(
                FulfillmentTask.sale_id == sale.id,
                FulfillmentTask.task_type == "PICKING",
            ))
            if not task:
                db.add(FulfillmentTask(
                    sale_id=sale.id,
                    warehouse_id=sale.warehouse_id,
                    task_type="PICKING",
                    status="OPEN",
                    company_id=sale.company_id,
                ))
            if sale.user_id:
                db.add(Notification(
                    user_id=sale.user_id,
                    type="success",
                    title="Pedido listo para picking",
                    message=f"La orden {str(sale.id)[:8]} tiene inventario reservado y está lista para preparar.",
                    link="/inventory/picking",
                ))
        elif event_type == "inventory.released" and sale:
            task = await db.scalar(select(FulfillmentTask).where(
                FulfillmentTask.sale_id == sale.id,
                FulfillmentTask.task_type == "PICKING",
            ))
            if task and task.status == "OPEN":
                task.status = "CANCELLED"
            if sale.user_id:
                db.add(Notification(
                    user_id=sale.user_id,
                    type="warning",
                    title="Reserva liberada",
                    message=f"La reserva de la orden {str(sale.id)[:8]} fue liberada.",
                    link="/sales",
                ))
        elif event_type == "inventory.dispatched" and sale:
            task = await db.scalar(select(FulfillmentTask).where(
                FulfillmentTask.sale_id == sale.id,
                FulfillmentTask.task_type == "PICKING",
            ))
            if task:
                task.status = "COMPLETED"
            if sale.user_id:
                db.add(Notification(
                    user_id=sale.user_id,
                    type="info",
                    title="Orden despachada",
                    message=f"La orden {str(sale.id)[:8]} fue despachada desde bodega.",
                    link="/sales",
                ))
            storefront_order = await db.scalar(select(StorefrontOrder).where(StorefrontOrder.sale_id == sale.id))
            if storefront_order and storefront_order.customer_email:
                customer_email = storefront_order.customer_email
                customer_name = storefront_order.customer_name
                order_code = str(sale.id)[:8].upper()
                customer_subject = f"Tu pedido #{order_code} fue enviado"
                customer_body = f"<p>Hola {customer_name},</p><p>Tu pedido <strong>#{order_code}</strong> ya fue despachado. Te avisaremos cuando sea entregado.</p>"
        elif event_type == "order.delivered" and sale:
            if sale.user_id:
                db.add(Notification(
                    user_id=sale.user_id,
                    type="success",
                    title="Orden entregada",
                    message=f"La orden {str(sale.id)[:8]} fue marcada como entregada.",
                    link="/sales",
                ))
            storefront_order = await db.scalar(select(StorefrontOrder).where(StorefrontOrder.sale_id == sale.id))
            if storefront_order and storefront_order.customer_email:
                customer_email = storefront_order.customer_email
                customer_name = storefront_order.customer_name
                order_code = str(sale.id)[:8].upper()
                customer_subject = f"Tu pedido #{order_code} fue entregado"
                customer_body = f"<p>Hola {customer_name},</p><p>Tu pedido <strong>#{order_code}</strong> fue entregado. Gracias por comprar con nosotros.</p>"
        elif event_type not in {"inventory.reserved", "inventory.released", "inventory.dispatched", "order.delivered"}:
            return False

        # The receipt and effects commit together. A crash or failed commit leaves
        # the stream message pending; a redelivery then safely retries everything.
        db.add(OutboxConsumption(event_id=parsed_event_id, consumer=GROUP))
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            return True
    if customer_email:
        # Dispatch emails are deliberately emitted only after the inventory
        # transaction succeeds. The receipt prevents duplicate sends on stream redelivery.
        await EmailService.send_email(
            customer_email,
            customer_subject,
            customer_body,
        )
    return True


async def main() -> None:
    # The blocking read must not inherit a socket timeout equal to its block
    # duration; otherwise an idle stream restarts the worker every few seconds.
    client = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=10)
    try:
        try:
            await client.xgroup_create(STREAM, GROUP, id="0-0", mkstream=True)
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise
        while True:
            # Reclaim deliveries left pending by a stopped worker before
            # reading fresh messages. This is what makes restarts safe.
            _next_id, claimed, _deleted = await client.xautoclaim(STREAM, GROUP, CONSUMER, min_idle_time=1000, start_id="0-0", count=20)
            messages = [(STREAM, claimed)] if claimed else []
            if not messages:
                try:
                    messages = await client.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=20, block=1000)
                except redis.TimeoutError:
                    continue
            for _stream, entries in messages:
                for message_id, values in entries:
                    try:
                        payload = json.loads(values.get("payload") or "{}")
                        if await process_event(values["event_id"], values["event_type"], payload):
                            await client.xack(STREAM, GROUP, message_id)
                    except Exception as exc:
                        # Leave unacknowledged so Redis can redeliver it.
                        print(f"Failed event {message_id}: {exc}")
                        continue
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
