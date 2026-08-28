"""Server-side tracking delivery for installed storefront marketing apps."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

import requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_definition import AppDefinition
from app.models.app_tracking_delivery import AppTrackingDelivery
from app.models.company_app_install import CompanyAppInstall
from app.models.sale import Sale
from app.models.storefront import StorefrontOrder
from app.services.outbox import enqueue_outbox_event

logger = logging.getLogger(__name__)

TRACKING_EVENT = "tracking.event"
TRACKING_PURCHASE_EVENT = "tracking.purchase"
APP_SLUGS = {"google-analytics", "meta-pixel", "tiktok-pixel"}

PROVIDER_EVENT_NAMES: dict[str, dict[str, str]] = {
    "google-analytics": {
        "page_view": "page_view",
        "view_item": "view_item",
        "search": "search",
        "add_to_cart": "add_to_cart",
        "remove_from_cart": "remove_from_cart",
        "view_cart": "view_cart",
        "begin_checkout": "begin_checkout",
        "add_shipping_info": "add_shipping_info",
        "add_payment_info": "add_payment_info",
        "purchase": "purchase",
    },
    "meta-pixel": {
        "page_view": "PageView",
        "view_item": "ViewContent",
        "search": "Search",
        "add_to_cart": "AddToCart",
        "remove_from_cart": "RemoveFromCart",
        "view_cart": "ViewCart",
        "begin_checkout": "InitiateCheckout",
        "add_shipping_info": "AddShippingInfo",
        "add_payment_info": "AddPaymentInfo",
        "purchase": "Purchase",
    },
    "tiktok-pixel": {
        "page_view": "PageView",
        "view_item": "ViewContent",
        "search": "Search",
        "add_to_cart": "AddToCart",
        "remove_from_cart": "RemoveFromCart",
        "view_cart": "ViewCart",
        "begin_checkout": "InitiateCheckout",
        "add_shipping_info": "AddShippingInfo",
        "add_payment_info": "AddPaymentInfo",
        "purchase": "Purchase",
    },
}


class TrackingRetryableError(RuntimeError):
    """A provider failure that should leave the outbox message pending."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class TrackingPermanentError(RuntimeError):
    """A provider rejected the event and retrying it will not help."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _hash_user_value(value: str | None, *, phone: bool = False) -> str | None:
    normalized = "".join(value.split()).lower() if value and not phone else "".join(
        character for character in (value or "") if character.isdigit()
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest() if normalized else None


def _tracking_items(sale: Sale) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in sale.items or []:
        product = item.product
        items.append({
            "item_id": str(getattr(product, "sku", None) or item.product_id),
            "item_name": str(getattr(product, "name", None) or "Producto"),
            "price": round(float(item.price or 0), 2),
            "quantity": max(1, float(item.quantity or 1)),
        })
    return items


def _event_name(payload: dict[str, Any]) -> str:
    return str(payload.get("name") or "purchase").strip().lower()


def _provider_event_name(app_slug: str, event_name: str) -> str | None:
    return PROVIDER_EVENT_NAMES.get(app_slug, {}).get(event_name)


def _clean_event_items(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for item in items[:100]:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("item_id") or "").strip()
        if not item_id:
            continue
        cleaned.append({
            "item_id": item_id[:200],
            "item_name": str(item.get("item_name") or "Producto")[:240],
            "price": max(0.0, round(float(item.get("price") or 0), 2)),
            "quantity": max(0.0, float(item.get("quantity") or 1)),
            **({"item_variant": str(item["item_variant"])[:200]} if item.get("item_variant") else {}),
            **({"item_category": str(item["item_category"])[:200]} if item.get("item_category") else {}),
            **({"item_brand": str(item["item_brand"])[:200]} if item.get("item_brand") else {}),
        })
    return cleaned


def enqueue_storefront_purchase_tracking(
    db: AsyncSession,
    storefront_order: StorefrontOrder,
    sale: Sale,
    *,
    source: str,
    transaction_id: str,
) -> None:
    """Queue one idempotent purchase event after a verified payment transition."""
    if not (storefront_order.tracking_consent_analytics or storefront_order.tracking_consent_marketing):
        return

    order_code = str(sale.id).split("-")[0].upper()
    payload = {
        "name": "purchase",
        "sale_id": str(sale.id),
        "storefront_id": str(storefront_order.storefront_id),
        "company_id": str(sale.company_id),
        "event_id": f"purchase:{order_code}",
        "transaction_id": order_code,
        "provider_transaction_id": transaction_id,
        "event_time": int(datetime.now(timezone.utc).timestamp()),
        "currency": str(storefront_order.currency or "USD").upper(),
        "value": round(float(sale.total or 0), 2),
        "items": _tracking_items(sale),
        "customer_email_hash": _hash_user_value(storefront_order.customer_email),
        "customer_phone_hash": _hash_user_value(storefront_order.customer_phone, phone=True),
        "consent": {
            "analytics": bool(storefront_order.tracking_consent_analytics),
            "marketing": bool(storefront_order.tracking_consent_marketing),
        },
        "source": source,
    }
    enqueue_outbox_event(
        db,
        event_type=TRACKING_PURCHASE_EVENT,
        aggregate_type="storefront_order",
        aggregate_id=sale.id,
        company_id=sale.company_id,
        payload=payload,
    )


def enqueue_storefront_tracking_event(
    db: AsyncSession,
    *,
    storefront_id: Any,
    company_id: Any,
    event: dict[str, Any],
) -> None:
    """Queue a browser-originated event without accepting server-side purchases."""
    name = _event_name(event)
    if name == "purchase":
        raise ValueError("Purchase events must come from a verified payment transition")

    event_id = str(event.get("event_id") or "").strip()
    if not event_id:
        raise ValueError("Tracking event has no event_id")
    consent = event.get("consent") if isinstance(event.get("consent"), dict) else {}
    payload = {
        "name": name,
        "storefront_id": str(storefront_id),
        "company_id": str(company_id),
        "event_id": event_id,
        "client_id": str(event.get("client_id") or "")[:255] or None,
        "event_time": int(datetime.now(timezone.utc).timestamp()),
        "currency": str(event.get("currency") or "USD").upper()[:12],
        "value": round(float(event.get("value") or 0), 2) if event.get("value") is not None else None,
        "transaction_id": str(event.get("transaction_id") or "")[:255] or None,
        "search_term": str(event.get("search_term") or "")[:240] or None,
        "page_location": str(event.get("page_location") or "")[:2048] or None,
        "items": _clean_event_items(event.get("items")),
        "consent": {
            "analytics": consent.get("analytics") is True,
            "marketing": consent.get("marketing") is True,
        },
        "source": "storefront_browser",
    }
    enqueue_outbox_event(
        db,
        event_type=TRACKING_EVENT,
        aggregate_type="storefront",
        aggregate_id=storefront_id,
        company_id=company_id,
        idempotency_key=f"{TRACKING_EVENT}:{storefront_id}:{event_id}",
        payload=payload,
    )


def _post_json(
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any],
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    try:
        response = requests.post(url, headers=headers, params=params, json=payload, timeout=12)
    except requests.RequestException as exc:
        raise TrackingRetryableError(str(exc)) from exc

    if response.status_code == 429 or response.status_code >= 500:
        raise TrackingRetryableError(f"provider returned HTTP {response.status_code}", response.status_code)
    if response.status_code >= 400:
        raise TrackingPermanentError(f"provider returned HTTP {response.status_code}", response.status_code)
    try:
        body = response.json() if getattr(response, "content", b"") else {}
    except ValueError:
        body = {}
    return body if isinstance(body, dict) else {}


def _meta_event(payload: dict[str, Any], private_settings: dict[str, Any], pixel_id: str) -> None:
    token = str(private_settings.get("access_token") or "").strip()
    if not token:
        return
    event_name = _provider_event_name("meta-pixel", _event_name(payload))
    if not event_name:
        return
    custom_data: dict[str, Any] = {"content_type": "product"}
    if payload.get("currency"):
        custom_data["currency"] = payload["currency"]
    if payload.get("value") is not None:
        custom_data["value"] = payload["value"]
    if payload.get("transaction_id"):
        custom_data["order_id"] = payload["transaction_id"]
    if payload.get("items"):
        custom_data["contents"] = [
            {"id": item["item_id"], "quantity": item["quantity"], "item_price": item["price"]}
            for item in payload["items"]
        ]
    if payload.get("search_term"):
        custom_data["search_string"] = payload["search_term"]
    event: dict[str, Any] = {
        "event_name": event_name,
        "event_time": payload["event_time"],
        "event_id": payload["event_id"],
        "action_source": "website",
        "user_data": {
            key: value
            for key, value in {
                "em": payload.get("customer_email_hash"),
                "ph": payload.get("customer_phone_hash"),
            }.items()
            if value
        },
        "custom_data": custom_data,
    }
    if payload.get("page_location"):
        event["event_source_url"] = payload["page_location"]
    request_body: dict[str, Any] = {"data": [event]}
    test_event_code = str(private_settings.get("test_event_code") or "").strip()
    if test_event_code:
        request_body["test_event_code"] = test_event_code
    body = _post_json(
        f"https://graph.facebook.com/v23.0/{pixel_id}/events",
        headers={"Content-Type": "application/json"},
        params={"access_token": token},
        payload=request_body,
    )
    if body.get("error"):
        raise TrackingPermanentError("Meta rejected the tracking event")


def _tiktok_event(payload: dict[str, Any], private_settings: dict[str, Any], pixel_id: str) -> None:
    token = str(private_settings.get("access_token") or "").strip()
    if not token:
        return
    event_name = _provider_event_name("tiktok-pixel", _event_name(payload))
    if not event_name:
        return
    properties: dict[str, Any] = {}
    if payload.get("currency"):
        properties["currency"] = payload["currency"]
    if payload.get("value") is not None:
        properties["value"] = payload["value"]
    if payload.get("search_term"):
        properties["query"] = payload["search_term"]
    if payload.get("items"):
        properties["contents"] = [
            {
                "content_id": item["item_id"],
                "content_name": item["item_name"],
                "content_type": "product",
                "quantity": item["quantity"],
                "price": item["price"],
            }
            for item in payload["items"]
        ]
    event_payload: dict[str, Any] = {
        "event_source": "web",
        "event_source_id": pixel_id,
        "data": [{
            "event": event_name,
            "event_time": payload["event_time"],
            "event_id": payload["event_id"],
            "user": {
                key: [value]
                for key, value in {
                    "email": payload.get("customer_email_hash"),
                    "phone": payload.get("customer_phone_hash"),
                }.items()
                if value
            },
            "properties": properties,
        }],
    }
    test_event_code = str(private_settings.get("test_event_code") or "").strip()
    if test_event_code:
        event_payload["test_event_code"] = test_event_code
    body = _post_json(
        "https://business-api.tiktok.com/open_api/v1.3/pixel/track/",
        headers={"Access-Token": token, "Content-Type": "application/json"},
        payload=event_payload,
    )
    if body.get("code") not in (None, 0, "0"):
        raise TrackingPermanentError("TikTok rejected the tracking event")


def _google_event(payload: dict[str, Any], private_settings: dict[str, Any], measurement_id: str) -> None:
    api_secret = str(private_settings.get("api_secret") or "").strip()
    if not api_secret:
        return
    event_name = _provider_event_name("google-analytics", _event_name(payload))
    if not event_name:
        return
    params: dict[str, Any] = {"event_id": payload["event_id"]}
    for key in ("currency", "value", "transaction_id", "search_term", "page_location"):
        if payload.get(key) is not None:
            params[key] = payload[key]
    if payload.get("items"):
        params["items"] = [
            {
                "item_id": item["item_id"],
                "item_name": item["item_name"],
                "price": item["price"],
                "quantity": item["quantity"],
            }
            for item in payload["items"]
        ]
    client_id = str(payload.get("client_id") or "").strip()
    if not client_id:
        client_id = f"server.{str(payload.get('sale_id') or payload['event_id']).replace('-', '')}"
    body = _post_json(
        "https://www.google-analytics.com/mp/collect",
        headers={"Content-Type": "application/json"},
        params={"measurement_id": measurement_id, "api_secret": api_secret},
        payload={
            "client_id": client_id,
            "events": [{"name": event_name, "params": params}],
        },
    )
    if body.get("error"):
        raise TrackingPermanentError("Google Analytics rejected the tracking event")


async def _get_delivery(
    db: AsyncSession,
    *,
    app_id: Any,
    install_id: Any,
    outbox_event_id: Any,
    provider: str,
    event_id: str,
    event_name: str,
    company_id: Any,
) -> AppTrackingDelivery:
    delivery = await db.scalar(
        select(AppTrackingDelivery).where(
            AppTrackingDelivery.app_id == app_id,
            AppTrackingDelivery.outbox_event_id == outbox_event_id,
        )
    )
    if delivery:
        return delivery
    delivery = AppTrackingDelivery(
        company_id=company_id,
        app_id=app_id,
        install_id=install_id,
        outbox_event_id=outbox_event_id,
        provider=provider,
        event_id=event_id,
        event_name=event_name,
        status="PENDING",
        attempt_number=0,
    )
    db.add(delivery)
    await db.flush()
    return delivery


def _mark_delivery(
    delivery: AppTrackingDelivery,
    *,
    status: str,
    error_message: str | None = None,
    status_code: int | None = None,
    attempted: bool = False,
) -> None:
    delivery.status = status
    delivery.status_code = status_code
    delivery.error_message = error_message[:2000] if error_message else None
    if attempted:
        delivery.attempt_number = int(delivery.attempt_number or 0) + 1
        delivery.last_attempt_at = datetime.utcnow()
    if status == "SENT":
        delivery.delivered_at = datetime.utcnow()
    else:
        delivery.delivered_at = None


async def send_server_side_tracking_event(
    db: AsyncSession,
    payload: dict[str, Any],
    *,
    outbox_event_id: Any = None,
) -> None:
    """Deliver one queued event to every matching, configured provider."""
    company_id = payload.get("company_id")
    if not company_id:
        logger.error("Discarding tracking event without a company")
        return
    event_name = _event_name(payload)
    supported_events = {name for names in PROVIDER_EVENT_NAMES.values() for name in names}
    if event_name not in supported_events:
        logger.error("Discarding unsupported tracking event: %s", event_name)
        return

    result = await db.execute(
        select(CompanyAppInstall, AppDefinition)
        .join(AppDefinition, AppDefinition.id == CompanyAppInstall.app_id)
        .where(
            CompanyAppInstall.company_id == company_id,
            CompanyAppInstall.is_enabled == True,
            AppDefinition.is_active == True,
            AppDefinition.slug.in_(APP_SLUGS),
        )
    )
    consent = payload.get("consent") if isinstance(payload.get("consent"), dict) else {}
    for install, app in result.all():
        settings = install.settings if isinstance(install.settings, dict) else {}
        if settings.get("server_side_enabled") is not True:
            continue
        consent_key = "analytics" if app.slug == "google-analytics" else "marketing"
        if consent.get(consent_key) is not True:
            continue
        if event_name != "page_view" and settings.get("track_ecommerce") is False:
            continue
        provider_event_name = _provider_event_name(app.slug, event_name)
        if not provider_event_name:
            continue

        delivery = await _get_delivery(
            db,
            app_id=app.id,
            install_id=install.id,
            outbox_event_id=outbox_event_id,
            provider=app.slug,
            event_id=str(payload.get("event_id") or ""),
            event_name=event_name,
            company_id=company_id,
        )
        if delivery.status in {"SENT", "FAILED", "NOT_CONFIGURED"}:
            continue

        private_settings = install.private_settings if isinstance(install.private_settings, dict) else {}
        tracking_id = str(
            settings.get("measurement_id") if app.slug == "google-analytics" else settings.get("pixel_id") or ""
        ).strip()
        secret_key = "api_secret" if app.slug == "google-analytics" else "access_token"
        secret = str(private_settings.get(secret_key) or "").strip()
        if not tracking_id or not secret:
            _mark_delivery(
                delivery,
                status="NOT_CONFIGURED",
                error_message=f"Falta configurar {secret_key} y el identificador del proveedor.",
            )
            continue

        try:
            if app.slug == "google-analytics":
                await asyncio.to_thread(_google_event, payload, private_settings, tracking_id.upper())
            elif app.slug == "meta-pixel":
                await asyncio.to_thread(_meta_event, payload, private_settings, tracking_id)
            elif app.slug == "tiktok-pixel":
                await asyncio.to_thread(_tiktok_event, payload, private_settings, tracking_id)
        except TrackingRetryableError as exc:
            _mark_delivery(
                delivery,
                status="RETRY",
                error_message=str(exc),
                status_code=exc.status_code,
                attempted=True,
            )
            # Persist the failed attempt before leaving the message pending in Redis.
            await db.commit()
            raise
        except TrackingPermanentError as exc:
            _mark_delivery(
                delivery,
                status="FAILED",
                error_message=str(exc),
                status_code=exc.status_code,
                attempted=True,
            )
            logger.warning("Server-side tracking rejected event for %s: %s", app.slug, exc)
        else:
            _mark_delivery(delivery, status="SENT", attempted=True)


async def send_server_side_purchase_events(
    db: AsyncSession,
    payload: dict[str, Any],
    *,
    outbox_event_id: Any = None,
) -> None:
    """Backward-compatible wrapper for purchase events."""
    await send_server_side_tracking_event(db, payload, outbox_event_id=outbox_event_id)
