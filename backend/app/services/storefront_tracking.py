"""Server-side ecommerce conversion delivery for installed tracking apps."""

from __future__ import annotations

import hashlib
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_definition import AppDefinition
from app.models.company_app_install import CompanyAppInstall
from app.models.sale import Sale
from app.models.storefront import StorefrontOrder
from app.services.outbox import enqueue_outbox_event

logger = logging.getLogger(__name__)

TRACKING_PURCHASE_EVENT = "tracking.purchase"
APP_SLUGS = {"google-analytics", "meta-pixel", "tiktok-pixel"}


class TrackingRetryableError(RuntimeError):
    """A provider failure that should leave the outbox message pending."""


class TrackingPermanentError(RuntimeError):
    """A provider rejected the event and retrying it will not help."""


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


def _post_json(url: str, *, headers: dict[str, str], payload: dict[str, Any], params: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        response = requests.post(url, headers=headers, params=params, json=payload, timeout=12)
    except requests.RequestException as exc:
        raise TrackingRetryableError(str(exc)) from exc

    if response.status_code == 429 or response.status_code >= 500:
        raise TrackingRetryableError(f"provider returned HTTP {response.status_code}")
    if response.status_code >= 400:
        raise TrackingPermanentError(f"provider returned HTTP {response.status_code}")
    try:
        body = response.json() if response.content else {}
    except ValueError:
        body = {}
    return body if isinstance(body, dict) else {}


def _meta_event(payload: dict[str, Any], private_settings: dict[str, Any], pixel_id: str) -> None:
    token = str(private_settings.get("access_token") or "").strip()
    if not token:
        return
    event = {
        "event_name": "Purchase",
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
        "custom_data": {
            "currency": payload["currency"],
            "value": payload["value"],
            "order_id": payload["transaction_id"],
            "content_type": "product",
            "contents": [
                {"id": item["item_id"], "quantity": item["quantity"], "item_price": item["price"]}
                for item in payload["items"]
            ],
        },
    }
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
        raise TrackingPermanentError("Meta rejected the purchase event")


def _tiktok_event(payload: dict[str, Any], private_settings: dict[str, Any], pixel_id: str) -> None:
    token = str(private_settings.get("access_token") or "").strip()
    if not token:
        return
    event_payload: dict[str, Any] = {
        "event_source": "web",
        "event_source_id": pixel_id,
        "data": [{
            "event": "Purchase",
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
            "properties": {
                "currency": payload["currency"],
                "value": payload["value"],
                "contents": [
                    {
                        "content_id": item["item_id"],
                        "content_name": item["item_name"],
                        "content_type": "product",
                        "quantity": item["quantity"],
                        "price": item["price"],
                    }
                    for item in payload["items"]
                ],
            },
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
        raise TrackingPermanentError("TikTok rejected the purchase event")


def _google_event(payload: dict[str, Any], private_settings: dict[str, Any], measurement_id: str) -> None:
    api_secret = str(private_settings.get("api_secret") or "").strip()
    if not api_secret:
        return
    body = _post_json(
        "https://www.google-analytics.com/mp/collect",
        headers={"Content-Type": "application/json"},
        params={"measurement_id": measurement_id, "api_secret": api_secret},
        payload={
            "client_id": f"server.{payload['sale_id'].replace('-', '')}",
            "events": [{
                "name": "purchase",
                "params": {
                    "transaction_id": payload["transaction_id"],
                    "currency": payload["currency"],
                    "value": payload["value"],
                    "items": [
                        {
                            "item_id": item["item_id"],
                            "item_name": item["item_name"],
                            "price": item["price"],
                            "quantity": item["quantity"],
                        }
                        for item in payload["items"]
                    ],
                },
            }],
        },
    )
    if body.get("error"):
        raise TrackingPermanentError("Google Analytics rejected the purchase event")


async def send_server_side_purchase_events(db: AsyncSession, payload: dict[str, Any]) -> None:
    """Deliver a queued purchase to each configured provider."""
    company_id = payload.get("company_id")
    if not company_id:
        raise TrackingPermanentError("Tracking payload has no company")
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
        allowed = consent.get("analytics") is True if app.slug == "google-analytics" else consent.get("marketing") is True
        if not allowed:
            continue
        private_settings = install.private_settings if isinstance(install.private_settings, dict) else {}
        try:
            if app.slug == "google-analytics":
                await asyncio.to_thread(
                    _google_event,
                    payload,
                    private_settings,
                    str(settings.get("measurement_id") or "").strip().upper(),
                )
            elif app.slug == "meta-pixel":
                await asyncio.to_thread(
                    _meta_event,
                    payload,
                    private_settings,
                    str(settings.get("pixel_id") or "").strip(),
                )
            elif app.slug == "tiktok-pixel":
                await asyncio.to_thread(
                    _tiktok_event,
                    payload,
                    private_settings,
                    str(settings.get("pixel_id") or "").strip(),
                )
        except TrackingPermanentError as exc:
            logger.warning("Server-side tracking rejected event for %s: %s", app.slug, exc)
