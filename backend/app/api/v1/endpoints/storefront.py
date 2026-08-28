import hashlib
import hmac
import asyncio
import secrets
import base64
import json
import logging
import mimetypes
from pathlib import Path
from html import escape
import re
import unicodedata
import uuid
from urllib.parse import quote, urlsplit
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, List
import requests
import dns.resolver

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only, selectinload
from sqlalchemy.orm.attributes import set_committed_value

from app.core import auth, security
from app.core.audit import log_activity, log_sale_event
from app.core.database import get_db
from app.core.permissions import PermissionChecker
from app.core.plan_limits import PlanLimitChecker
from app.core.config import settings
from app.core.rate_limit import limiter
from app.models.branch import Branch
from app.models.warehouse import Warehouse
from app.models.company import Company
from app.models.brand import Brand
from app.models.category import Category
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.sale import Payment, Sale, SaleItem, SaleStatus
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.product_variant import ProductVariant
from app.models.user import User
from app.models.client import Client
from app.models.pricelist import PriceList
from app.models.storefront_customer import StorefrontCustomerAccount
from app.models.storefront_newsletter import StorefrontNewsletterSubscription
from app.services.email import EmailService
from app.services.outbox import enqueue_outbox_event
from app.models.storefront import (
    PublishedProduct,
    StoreCollection,
    StoreCollectionProduct,
    StoreNavigationItem,
    StorePaymentGateway,
    StorefrontShippingDestination,
    StorefrontShippingMethod,
    StorefrontShippingRule,
    Storefront,
    StorefrontDomain,
    StorefrontOrder,
)
from app.models.storefront_coupon import StorefrontCoupon
from app.models.storefront_theme import (
    StorefrontThemeDocument as StorefrontThemeDocumentModel,
    StorefrontThemeRevision as StorefrontThemeRevisionModel,
)
from app.models.storefront_media import StorefrontMediaAsset
from app.services.image_upload import save_image_upload, upload_root
from app.schemas import storefront as schemas
from app.services.storefront_theme import (
    build_cart_document,
    build_collection_document,
    build_home_document,
    build_pages_document,
    build_product_document,
    build_search_document,
    component_registry,
    normalize_collection_document,
    normalize_cart_document,
    normalize_home_document,
    normalize_pages_document,
    normalize_product_document,
    normalize_search_document,
    validate_template_key,
)
from app.services.storefront_checkout import normalize_checkout_settings
from app.services.storefront_shipping import (
    calculate_shipping,
    ensure_default_shipping_configuration,
    validate_shipping_rule_values,
)
from app.services.pricing import ProductPricing, load_price_list_context, resolve_price, resolve_product_pricing
from app.core.credential_crypto import SENSITIVE_GATEWAY_CONFIG_KEYS

router = APIRouter()
logger = logging.getLogger(__name__)

# Providers that have a complete checkout path in this application. New
# providers must add a signed intent and payment-status verification before
# being exposed to customers.
SUPPORTED_PUBLIC_PAYMENT_PROVIDERS = {
    "wompi", "payu", "mercadopago", "addi", "sistecredito",
    "whatsapp", "cod", "manual_transfer",
}
# Keep authenticated media reads/deletes aligned with the same shared static
# volume used by the upload service (/app/static in production).
STATIC_ASSET_ROOT = upload_root().parent
RESERVED_STOREFRONT_SUBDOMAINS = {
    "www", "api", "admin", "app", "panel", "mail", "static", "cdn", "support", "help",
}
MAX_STOREFRONT_MEDIA_ASSETS = 200


def _platform_storefront_host_and_port() -> tuple[str, int | None]:
    raw_value = (settings.PLATFORM_STOREFRONT_DOMAIN or "").strip().lower().rstrip(".")
    if not raw_value:
        return "", None
    try:
        parsed = urlsplit(raw_value if "://" in raw_value else f"//{raw_value}")
        host = (parsed.hostname or "").rstrip(".")
        port = parsed.port
    except ValueError:
        return "", None
    if (
        not host
        or not re.fullmatch(r"[a-z0-9.-]+", host)
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        return "", None
    return host, port


def _normalize_public_asset_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if candidate.startswith("/static/"):
        return candidate
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return None
    return parsed.path if parsed.path.startswith("/static/") else None


def _contains_public_asset(value: Any, asset_url: str) -> bool:
    if isinstance(value, str):
        return _normalize_public_asset_url(value) == asset_url
    if isinstance(value, dict):
        return any(_contains_public_asset(item, asset_url) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_public_asset(item, asset_url) for item in value)
    return False


def _resolve_public_asset_path(asset_path: str) -> tuple[str, Path]:
    parts = [part for part in asset_path.strip("/").split("/") if part]
    if (
        len(parts) < 2
        or parts[0] != "static"
        or any(part in {".", ".."} or "\\" in part for part in parts)
    ):
        raise HTTPException(status_code=404, detail="Asset not found")

    relative_path = Path(*parts[1:])
    root = STATIC_ASSET_ROOT.resolve()
    candidate = (root / relative_path).resolve()
    if root not in candidate.parents or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    media_type = mimetypes.guess_type(candidate.name)[0] or ""
    if not media_type.startswith("image/"):
        raise HTTPException(status_code=404, detail="Asset not found")
    return "/" + "/".join(parts), candidate


async def _public_asset_is_referenced(
    db: AsyncSession,
    storefront: Storefront,
    asset_url: str,
    preview_token: str | None = None,
) -> bool:
    published_reference = await db.scalar(
        select(Product.id)
        .join(PublishedProduct, PublishedProduct.product_id == Product.id)
        .outerjoin(ProductImage, ProductImage.product_id == Product.id)
        .where(
            PublishedProduct.storefront_id == storefront.id,
            PublishedProduct.company_id == storefront.company_id,
            PublishedProduct.is_active == True,
            PublishedProduct.is_published == True,
            or_(
                Product.image_url == asset_url,
                ProductImage.image_url == asset_url,
            ),
        )
        .limit(1)
    )
    if published_reference:
        return True

    collection_reference = await db.scalar(
        select(StoreCollection.id).where(
            StoreCollection.storefront_id == storefront.id,
            StoreCollection.company_id == storefront.company_id,
            StoreCollection.is_active == True,
            StoreCollection.image_url == asset_url,
        ).limit(1)
    )
    if collection_reference:
        return True

    media_reference = await db.scalar(
        select(StorefrontMediaAsset.id).where(
            StorefrontMediaAsset.storefront_id == storefront.id,
            StorefrontMediaAsset.company_id == storefront.company_id,
            StorefrontMediaAsset.storage_path == asset_url,
            StorefrontMediaAsset.is_active == True,
        ).limit(1)
    )
    if media_reference:
        return True

    theme_document = await db.scalar(
        select(StorefrontThemeDocumentModel).where(
            StorefrontThemeDocumentModel.storefront_id == storefront.id,
            StorefrontThemeDocumentModel.company_id == storefront.company_id,
            StorefrontThemeDocumentModel.template_key == "home",
            StorefrontThemeDocumentModel.is_active == True,
        )
    )
    if theme_document:
        if _contains_public_asset(theme_document.published_document, asset_url):
            return True
        preview_claims = auth.get_storefront_preview_claims(preview_token) if preview_token else None
        if preview_claims and preview_claims[:2] == (storefront.id, storefront.company_id):
            if _contains_public_asset(theme_document.draft_document, asset_url):
                return True

    company = await _get_company_for_storefront(db, storefront)
    return any(
        _contains_public_asset(value, asset_url)
        for value in (
            company.logo_url if company else None,
            storefront.theme_settings,
            storefront.checkout_settings,
            storefront.seo_settings,
        )
    )
def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_custom_domain(value: str) -> str:
    """Accept a host only; never a URL, wildcard, port, or local address."""
    domain = (value or "").strip().lower().rstrip(".")
    if not domain or "://" in domain or "/" in domain or ":" in domain or "@" in domain:
        raise HTTPException(status_code=422, detail="Ingresa solo el dominio, por ejemplo tienda.midominio.com.")
    try:
        domain = domain.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise HTTPException(status_code=422, detail="El dominio no es válido.") from exc
    if len(domain) > 253 or domain in {"localhost", "127.0.0.1"} or "." not in domain:
        raise HTTPException(status_code=422, detail="Ingresa un dominio público válido.")
    for label in domain.split("."):
        if not label or len(label) > 63 or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label):
            raise HTTPException(status_code=422, detail="El dominio no es válido.")
    return domain


def _domain_verification_record(domain: str) -> str:
    return f"_lumefy-verification.{domain}"


def _domain_verification_value(token: str) -> str:
    return f"lumefy-verification={token}"


def _serialize_domain(domain: StorefrontDomain) -> schemas.StorefrontDomain:
    token = domain.verification_token
    return schemas.StorefrontDomain(
        id=domain.id,
        storefront_id=domain.storefront_id,
        domain=domain.domain,
        is_primary=domain.is_primary,
        is_verified=domain.is_verified,
        verification_token=token,
        verification_record=_domain_verification_record(domain.domain) if token else None,
        verification_value=_domain_verification_value(token) if token else None,
        verified_at=domain.verified_at,
        company_id=domain.company_id,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
        is_active=domain.is_active,
    )


async def _ensure_domain_verification_token(domain: StorefrontDomain) -> bool:
    if domain.verification_token:
        return False
    domain.verification_token = secrets.token_urlsafe(24)
    domain.is_verified = False
    domain.verified_at = None
    return True


async def _verify_domain_txt_record(domain: StorefrontDomain) -> bool:
    if not domain.verification_token:
        return False
    expected = _domain_verification_value(domain.verification_token)

    def resolve_txt() -> list[str]:
        resolver = dns.resolver.Resolver(configure=True)
        resolver.timeout = 3
        resolver.lifetime = 5
        answers = resolver.resolve(_domain_verification_record(domain.domain), "TXT")
        return [b"".join(answer.strings).decode("utf-8") for answer in answers]

    try:
        records = await asyncio.to_thread(resolve_txt)
    except (dns.exception.DNSException, UnicodeDecodeError):
        return False
    return expected in records


async def _resolve_public_checkout_adjustments(
    db: AsyncSession,
    storefront: Storefront,
    payload: Any,
    subtotal: float,
    rows: list[Any] | None = None,
) -> tuple[float, Any]:
    """Calculate checkout adjustments exclusively from storefront server settings."""
    discount = _safe_float(getattr(payload, "discount_amount", 0))
    shipping = _safe_float(getattr(payload, "shipping_amount", 0))
    coupon_code = _safe_string(getattr(payload, "coupon_code", None))

    if discount < 0 or shipping < 0:
        raise HTTPException(status_code=400, detail="Checkout adjustments cannot be negative")
    if discount > 0 or shipping > 0:
        raise HTTPException(
            status_code=400,
            detail="Descuentos, cupones y envío deben calcularse con las reglas configuradas de la tienda",
        )
    calculated_discount = 0.0
    if coupon_code:
        now = datetime.now(timezone.utc)
        coupon = await db.scalar(select(StorefrontCoupon).where(
            StorefrontCoupon.storefront_id == storefront.id,
            StorefrontCoupon.code == coupon_code.upper(),
            StorefrontCoupon.company_id == storefront.company_id,
            StorefrontCoupon.is_active == True,
            StorefrontCoupon.is_enabled == True,
        ))
        if not coupon or (coupon.starts_at and coupon.starts_at > now) or (coupon.ends_at and coupon.ends_at < now):
            raise HTTPException(status_code=400, detail="Cupón inválido o vencido")
        if subtotal < coupon.minimum_amount:
            raise HTTPException(status_code=400, detail=f"El cupón requiere una compra mínima de {coupon.minimum_amount:g}")
        calculated_discount = subtotal * coupon.value / 100 if coupon.discount_type == "PERCENT" else coupon.value
        calculated_discount = min(subtotal, calculated_discount)
    if rows is None:
        settings = storefront.checkout_settings or {}
        flat_shipping = max(0.0, _safe_float(settings.get("flat_shipping_rate")))
        free_shipping_threshold = max(0.0, _safe_float(settings.get("free_shipping_threshold")))
        calculated_shipping = 0.0 if free_shipping_threshold and subtotal >= free_shipping_threshold else flat_shipping
        return calculated_discount, calculated_shipping

    shipping = await calculate_shipping(
        db,
        storefront,
        rows,
        subtotal,
        address=getattr(payload, "address", None),
        payment_provider=getattr(payload, "payment_provider", None),
        method_id=getattr(payload, "shipping_method_id", None),
    )
    return calculated_discount, shipping


def _calculate_checkout_tax(
    storefront: Storefront,
    subtotal: float,
    discount: float,
    shipping: float,
) -> float:
    """Calculate tax only from the storefront's server-side checkout policy."""
    config = storefront.checkout_settings or {}
    rate = max(0.0, _safe_float(config.get("tax_rate")))
    if not rate:
        return 0.0
    taxable_amount = max(0.0, subtotal - discount)
    if bool(config.get("tax_shipping")):
        taxable_amount += max(0.0, shipping)
    divisor = 1 + (rate / 100)
    if bool(config.get("tax_included")):
        return round(taxable_amount - (taxable_amount / divisor), 2)
    return round(taxable_amount * (rate / 100), 2)


def _safe_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _slugify_storefront(value: str) -> str:
    """Create a URL-safe, deterministic identifier from a store name."""
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return (slug or "tienda")[:48].rstrip("-")


async def _available_storefront_slug(db: AsyncSession, company_id: uuid.UUID, name: str) -> str:
    """Generate a company-local slug, retaining old URLs when a store is renamed."""
    base = _slugify_storefront(name)
    candidate = base
    suffix = 2
    while await db.scalar(
        select(Storefront.id).where(
            Storefront.company_id == company_id,
            func.lower(Storefront.slug) == candidate.lower(),
        ).limit(1)
    ):
        candidate = f"{base[: max(1, 48 - len(str(suffix)) - 1)]}-{suffix}"
        suffix += 1
    return candidate


async def _available_storefront_subdomain(db: AsyncSession, name: str) -> str:
    """Generate a globally unique platform subdomain, including inactive rows."""
    base = _slugify_storefront(name)
    if base in RESERVED_STOREFRONT_SUBDOMAINS:
        base = f"{base}-store"
    candidate = base
    suffix = 2
    while await db.scalar(
        select(Storefront.id).where(
            Storefront.subdomain.is_not(None),
            func.lower(Storefront.subdomain) == candidate.lower(),
        ).limit(1)
    ):
        candidate = f"{base[: max(1, 48 - len(str(suffix)) - 1)]}-{suffix}"
        suffix += 1
    return candidate


def _format_payu_confirmation_amount(value: Any) -> str:
    """Match PayU's confirmation-signature amount formatting exactly."""
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid PayU confirmation amount") from exc
    return f"{amount:.1f}" if amount == amount.quantize(Decimal("1")) else f"{amount:.2f}"


def _has_valid_payu_confirmation_signature(payload: dict[str, Any], api_key: str | None) -> bool:
    """Validate PayU's MD5 confirmation signature before touching an order."""
    if not api_key:
        return False
    merchant_id = _safe_string(payload.get("merchant_id"))
    reference_sale = _safe_string(payload.get("reference_sale"))
    currency = _safe_string(payload.get("currency"))
    state_pol = _safe_string(payload.get("state_pol"))
    received_signature = _safe_string(payload.get("sign"))
    if not all((merchant_id, reference_sale, currency, state_pol, received_signature)):
        return False
    try:
        amount = _format_payu_confirmation_amount(payload.get("value"))
    except HTTPException:
        return False
    raw = f"{api_key}~{merchant_id}~{reference_sale}~{amount}~{currency}~{state_pol}"
    expected_signature = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return hmac.compare_digest(expected_signature.lower(), received_signature.lower())


def _has_valid_mercadopago_webhook_signature(
    payload: dict[str, Any],
    signature_header: str | None,
    request_id: str | None,
    secret: str | None,
) -> bool:
    """Validate Mercado Pago's HMAC notification manifest when a secret is configured."""
    if not secret or not signature_header or not request_id:
        return False
    parts: dict[str, str] = {}
    for item in signature_header.split(","):
        key, separator, value = item.strip().partition("=")
        if separator and key and value:
            parts[key.strip()] = value.strip()
    timestamp = parts.get("ts")
    received_signature = parts.get("v1")
    data = payload.get("data") or {}
    payment_id = _safe_string(data.get("id") if isinstance(data, dict) else None)
    if not timestamp or not received_signature or not payment_id:
        return False
    manifest = f"id:{payment_id};request-id:{request_id};ts:{timestamp};"
    expected_signature = hmac.new(secret.encode("utf-8"), manifest.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_signature.lower(), received_signature.lower())


def _has_valid_basic_auth(
    authorization: str | None,
    username: str | None,
    password: str | None,
) -> bool:
    if not authorization or not username or not password:
        return False
    expected = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return hmac.compare_digest(authorization, f"Basic {expected}")


async def _get_storefront_order_for_payment_webhook(
    db: AsyncSession,
    storefront_id: uuid.UUID,
    sale_id: uuid.UUID,
    provider: str,
) -> StorefrontOrder:
    storefront_order = await db.scalar(
        select(StorefrontOrder)
        .options(
            selectinload(StorefrontOrder.sale).selectinload(Sale.items).selectinload(SaleItem.product),
            selectinload(StorefrontOrder.storefront),
        )
        .where(
            StorefrontOrder.storefront_id == storefront_id,
            StorefrontOrder.sale_id == sale_id,
            StorefrontOrder.is_active == True,
        )
    )
    if not storefront_order or not storefront_order.sale or not storefront_order.storefront:
        raise HTTPException(status_code=404, detail="Checkout order not found")
    if storefront_order.payment_provider != provider:
        raise HTTPException(status_code=400, detail="Payment provider does not match the checkout order")
    return storefront_order


async def _apply_gateway_payment_status(
    db: AsyncSession,
    storefront_order: StorefrontOrder,
    provider: str,
    status: str,
    transaction_id: str,
) -> str:
    """Persist a verified provider result and safely confirm inventory once."""
    sale = storefront_order.sale
    if not sale:
        raise HTTPException(status_code=404, detail="Checkout order not found")
    normalized_status = status.lower()
    previous_status = (storefront_order.payment_status or "").lower()
    if previous_status == "approved" and normalized_status != "approved":
        await log_sale_event(
            db,
            sale_id=str(sale.id),
            company_id=str(sale.company_id),
            event_type="PAYMENT_STATUS_IGNORED",
            title="Actualización de pago ignorada",
            description="Se recibió un estado posterior distinto a un pago ya aprobado.",
            status="warning",
            provider=provider,
            reference=transaction_id,
            metadata={"current": previous_status, "received": normalized_status},
        )
        await db.commit()
        return "ignored"

    payment = await db.scalar(
        select(Payment).where(
            Payment.sale_id == sale.id,
            Payment.method == provider,
            Payment.is_active == True,
        )
    )
    if payment:
        payment.reference = transaction_id
        db.add(payment)

    storefront_order.payment_status = normalized_status
    if normalized_status == "approved":
        if not await _reserve_storefront_sale(db, sale):
            storefront_order.payment_status = "approved_stock_unavailable"
    elif normalized_status in {"declined", "cancelled", "expired", "rejected"} and sale.status in {
        SaleStatus.DRAFT,
        SaleStatus.QUOTE,
        SaleStatus.CONFIRMED,
    }:
        await _cancel_storefront_sale_and_release_reservation(db, sale)

    final_status = (storefront_order.payment_status or normalized_status).lower()
    if previous_status != final_status:
        await log_sale_event(
            db,
            sale_id=str(sale.id),
            company_id=str(sale.company_id),
            event_type="PAYMENT_STATUS_UPDATED",
            title="Estado de pago actualizado",
            description=f"El proveedor reportó el pago como {final_status.upper()}.",
            status="success" if final_status in {"approved", "approved_partial"} else "warning" if final_status in {"declined", "cancelled", "expired", "rejected"} else "pending",
            provider=provider,
            reference=transaction_id,
            metadata={"from": previous_status or "none", "to": final_status},
        )

    db.add(storefront_order)
    db.add(sale)
    await db.commit()
    if previous_status != storefront_order.payment_status and storefront_order.payment_status in {
        "approved",
        "approved_stock_unavailable",
        "declined",
        "rejected",
        "cancelled",
        "expired",
    }:
        await _send_storefront_payment_status_email(storefront_order)
    return storefront_order.payment_status


async def _send_storefront_payment_status_email(storefront_order: StorefrontOrder) -> None:
    """Best-effort customer notification; payment persistence must never depend on SMTP."""
    storefront = storefront_order.storefront
    sale = storefront_order.sale
    if not storefront or not sale or not storefront_order.customer_email:
        return
    status = (storefront_order.payment_status or "pending").lower()
    order_code = str(sale.id).split("-")[0].upper()
    if status == "approved":
        title = "Pago confirmado"
        message = "Confirmamos tu pago. Prepararemos el pedido y te avisaremos cuando avance."
    elif status == "approved_stock_unavailable":
        title = "Pago recibido; pedido en revisión"
        message = "Recibimos tu pago y el equipo revisará la disponibilidad antes de preparar el pedido."
    else:
        title = "No pudimos confirmar el pago"
        message = "El pago no se completó. Puedes intentar de nuevo con otro método de pago."
    subject = f"{storefront.name} · {title} · Pedido #{order_code}"
    html_content = f"""
    <html><body style="font-family:Arial,sans-serif;color:#1f2937">
      <div style="max-width:560px;margin:0 auto;padding:24px;border:1px solid #e5e7eb;border-radius:12px">
        <h2 style="margin:0 0 16px">{escape(title)}</h2>
        <p>Hola {escape(storefront_order.customer_name)},</p>
        <p>{escape(message)}</p>
        <p><strong>Pedido:</strong> #{order_code}<br/><strong>Total:</strong> {escape(storefront_order.currency)} {float(sale.total):,.2f}</p>
      </div>
    </body></html>
    """
    try:
        await EmailService.send_email(storefront_order.customer_email, subject, html_content)
    except Exception:
        # EmailService logs the provider failure. The gateway acknowledgement
        # must stay successful so providers do not repeat a settled payment.
        return


def _pick_first(*values: Any) -> Any:
    for value in values:
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
            continue
        if value is not None:
            return value
    return None


def _theme_dict(storefront: Storefront) -> dict:
    return storefront.theme_settings if isinstance(storefront.theme_settings, dict) else {}


def _branding_dict(storefront: Storefront) -> dict:
    theme_settings = _theme_dict(storefront)
    branding = theme_settings.get("branding")
    return branding if isinstance(branding, dict) else {}


def _social_links_payload(storefront: Storefront) -> dict:
    theme_settings = _theme_dict(storefront)
    branding = _branding_dict(storefront)
    social_links = branding.get("social_links")
    if not isinstance(social_links, dict):
        social_links = theme_settings.get("social_links")
    if not isinstance(social_links, dict):
        social_links = {}

    return {
        "facebook": _pick_first(social_links.get("facebook"), branding.get("facebook"), theme_settings.get("facebook")),
        "twitter": _pick_first(social_links.get("twitter"), branding.get("twitter"), theme_settings.get("twitter")),
        "instagram": _pick_first(social_links.get("instagram"), branding.get("instagram"), theme_settings.get("instagram")),
        "linkedin": _pick_first(social_links.get("linkedin"), branding.get("linkedin"), theme_settings.get("linkedin")),
    }


def _promo_banners_payload(storefront: Storefront) -> list[dict]:
    theme_settings = _theme_dict(storefront)
    branding = _branding_dict(storefront)
    banners = branding.get("promo_banners")
    if not isinstance(banners, list):
        banners = theme_settings.get("promo_banners")
    if not isinstance(banners, list):
        return []

    payload: list[dict] = []
    for index, banner in enumerate(banners):
        if not isinstance(banner, dict):
            continue
        title = _safe_string(banner.get("title"))
        if not title:
            continue
        payload.append(
            {
                "id": _safe_string(banner.get("id")) or f"promo-{index + 1}",
                "title": title,
                "subtitle": _safe_string(banner.get("subtitle")),
                "description": _safe_string(banner.get("description")),
                "cta_label": _safe_string(banner.get("cta_label")) or "Buy Now",
                "cta_href": _safe_string(banner.get("cta_href")) or "#",
                "image_url": _safe_string(banner.get("image_url")),
                "background_color": _safe_string(banner.get("background_color")),
                "accent_color": _safe_string(banner.get("accent_color")),
            }
        )
    return payload


async def _get_company_for_storefront(db: AsyncSession, storefront: Storefront) -> Company | None:
    if not storefront.company_id:
        return None
    result = await db.execute(
        select(Company).where(
            Company.id == storefront.company_id,
            Company.is_active == True,
        )
    )
    return result.scalars().first()


def _serialize_public_branding(storefront: Storefront, company: Company | None) -> schemas.PublicStorefrontBranding:
    theme_settings = _theme_dict(storefront)
    branding = _branding_dict(storefront)
    support_address = _pick_first(
        branding.get("support_address"),
        theme_settings.get("support_address"),
        company.address if company else None,
    )
    footer_text = _pick_first(
        branding.get("footer_text"),
        theme_settings.get("footer_text"),
        f"{storefront.name}. Todos los derechos reservados.",
    )

    return schemas.PublicStorefrontBranding(
        logo_url=_pick_first(branding.get("logo_url"), theme_settings.get("logo_url"), company.logo_url if company else None),
        support_phone=_pick_first(branding.get("support_phone"), theme_settings.get("support_phone"), company.phone if company else None),
        support_email=_pick_first(branding.get("support_email"), theme_settings.get("support_email"), company.email if company else None),
        support_address=support_address,
        website=_pick_first(branding.get("website"), theme_settings.get("website"), company.website if company else None),
        footer_text=footer_text,
        social_links=_social_links_payload(storefront),
        promo_banners=_promo_banners_payload(storefront),
    )


def _serialize_public_account_user(
    account: StorefrontCustomerAccount,
) -> schemas.PublicStorefrontAccountUser:
    return schemas.PublicStorefrontAccountUser(
        id=account.id,
        email=account.email,
        full_name=account.full_name,
        created_at=account.created_at,
    )


async def _get_current_storefront_customer(
    storefront_id: uuid.UUID,
    db: AsyncSession,
    current_account: StorefrontCustomerAccount,
) -> tuple[Storefront, StorefrontCustomerAccount]:
    storefront = await _get_public_storefront_by_id(db, storefront_id)
    if current_account.storefront_id != storefront.id:
        raise HTTPException(status_code=403, detail="Storefront account access denied")
    return storefront, current_account


def _create_storefront_access_token(
    account: StorefrontCustomerAccount,
    storefront: Storefront,
) -> str:
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return auth.create_access_token(
        data={
            "sub": str(account.id),
            "customer_account_id": str(account.id),
            "scope": "storefront",
            "storefront_id": str(storefront.id),
        },
        expires_delta=expires,
    )


def _extract_note_value(notes: str | None, key: str) -> str | None:
    if not notes:
        return None
    prefix = f"{key}="
    for part in notes.split(" | "):
        if part.startswith(prefix):
            value = part[len(prefix):].strip()
            return value or None
    return None


def _map_sale_status_to_order_status(status: SaleStatus | str) -> str:
    value = status.value if isinstance(status, SaleStatus) else str(status)
    normalized = value.lower()
    if normalized in {"delivered", "completed"}:
        return "delivered"
    if normalized in {"cancelled"}:
        return "on-hold"
    return "processing"


def _normalize_checkout_text(value: Any) -> str | None:
    return _safe_string(value)


def _build_checkout_order_response(
    storefront: Storefront,
    sale: Sale,
    payment_provider: str,
    payment_status: str = "pending",
) -> schemas.PublicCheckoutCreateOrderResponse:
    return schemas.PublicCheckoutCreateOrderResponse(
        order_id=sale.id,
        order_code=str(sale.id).split("-")[0].upper(),
        status=str(sale.status.value if isinstance(sale.status, SaleStatus) else sale.status),
        currency=storefront.currency,
        subtotal=float(sale.subtotal or 0.0),
        discount=float(sale.discount or 0.0),
        shipping=float(sale.shipping_cost or 0.0),
        tax=float(sale.tax or 0.0),
        total=float(sale.total or 0.0),
        payment_provider=payment_provider,
        payment_status=payment_status,
        shipping_method_id=getattr(sale.__dict__.get("storefront_order"), "shipping_method_id", None),
        shipping_method_name=getattr(sale.__dict__.get("storefront_order"), "shipping_method_name", None),
        shipping_quote_required=bool(getattr(sale.__dict__.get("storefront_order"), "shipping_quote_required", False)),
    )


async def _get_storefront_customer_account_by_email(
    db: AsyncSession,
    storefront: Storefront,
    email: str | None,
) -> StorefrontCustomerAccount | None:
    normalized_email = _safe_string(email)
    if not normalized_email:
        return None

    result = await db.execute(
        select(StorefrontCustomerAccount).where(
            StorefrontCustomerAccount.storefront_id == storefront.id,
            func.lower(StorefrontCustomerAccount.email) == normalized_email.lower(),
            StorefrontCustomerAccount.is_active == True,
        )
    )
    return result.scalars().first()


async def _get_or_create_storefront_client(
    db: AsyncSession,
    storefront: Storefront,
    payload: schemas.PublicCheckoutCreateOrderRequest,
) -> Client | None:
    email = payload.customer.email.strip().lower()
    if not email:
        return None

    result = await db.execute(
        select(Client).where(
            Client.company_id == storefront.company_id,
            Client.email == email,
            Client.is_active == True,
        )
    )
    client = result.scalars().first()
    full_name = payload.customer.full_name.strip()

    if client:
        client.name = full_name
        client.phone = payload.customer.phone or client.phone
        client.tax_id = payload.customer.document_id or client.tax_id
        client.address = payload.address.line1 or client.address
        db.add(client)
        await db.flush()
        return client

    client = Client(
        name=full_name,
        email=email,
        phone=payload.customer.phone,
        tax_id=payload.customer.document_id,
        address=payload.address.line1,
        status="active",
        notes="Auto-created from storefront checkout",
        company_id=storefront.company_id,
    )
    db.add(client)
    await db.flush()
    return client


def _storefront_reset_link(storefront: Storefront, token: str) -> str:
    base_url = settings.FRONTEND_URL.rstrip("/")
    platform_domain, platform_port = _platform_storefront_host_and_port()
    subdomain = (storefront.subdomain or "").strip().lower().strip(".")
    if platform_domain and subdomain:
        scheme = "http" if platform_domain in {"localhost", "127.0.0.1"} else "https"
        port_suffix = f":{platform_port}" if platform_port else ""
        base_url = f"{scheme}://{subdomain}.{platform_domain}{port_suffix}"
    return f"{base_url}/password/reset?token={token}&storefront_id={storefront.id}"


def _split_variant_tokens(value: str | None) -> list[str]:
    if not value:
        return []
    # Keep hyphens intact in dimension labels (for example,
    # "Doble - 1.40 x 1.90"), while still supporting simple "Rojo - XL"
    # names from integrations.
    # Commas inside decimal dimensions are part of the value (for example,
    # "0,40 X 0,70 Aprox."). Only treat a comma followed by whitespace as a
    # separator used by simpler integrations such as "Rojo, XL".
    normalized = re.sub(r",\s+", "/", value.replace("|", "/"))
    tokens: list[str] = []
    for part in normalized.split("/"):
        compact = part.strip()
        if not compact:
            continue
        if "-" in compact and not re.search(r"\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?", compact):
            hyphen_parts = [item.strip() for item in compact.split("-") if item.strip()]
            if len(hyphen_parts) > 1:
                tokens.extend(hyphen_parts)
                continue
        tokens.append(compact)
    return tokens


def _normalized_variant_attributes(variant: ProductVariant) -> dict[str, Any]:
    attributes = variant.attributes if isinstance(variant.attributes, dict) else {}
    return {str(key).strip().lower(): value for key, value in attributes.items()}


def _is_measure_label(value: str) -> bool:
    normalized = unicodedata.normalize("NFD", value.lower())
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return bool(
        re.search(r"\b(?:xs|s|m|l|xl|xxl|xxxl|2xl|3xl|4xl|5xl)\b", normalized)
        or re.search(
            r"\b(?:doble|sencilla|queen|king|semidoble|individual|matrimonial|twin|full)\b",
            normalized,
        )
        or re.fullmatch(r"\d+(?:[.,]\d+)?", normalized)
        or re.search(r"\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?", normalized)
    )


def _extract_variant_facets(variants: list[ProductVariant] | None) -> tuple[list[str], list[str]]:
    if not variants:
        return [], []

    sizes: list[str] = []
    colors: list[str] = []
    seen_sizes: set[str] = set()
    seen_colors: set[str] = set()

    for variant in variants:
        attributes = _normalized_variant_attributes(variant)
        explicit_size = next(
            (
                str(attributes[key]).strip()
                for key in ("size", "sizes", "talla", "tallas", "medida", "medidas")
                if attributes.get(key) not in (None, "")
            ),
            None,
        )
        explicit_color = next(
            (
                str(attributes[key]).strip()
                for key in ("color", "colour", "colored")
                if attributes.get(key) not in (None, "")
            ),
            None,
        )

        # Prefer explicit attributes. If an integration only sends a variant
        # name, retain the complete measure instead of splitting its numbers
        # into unrelated color facets.
        name = str(variant.name or "").strip()
        name_tokens = _split_variant_tokens(name)
        measure_tokens = [token for token in name_tokens if _is_measure_label(token)]
        if explicit_size:
            # When the explicit value is only "Doble" but the variant name
            # carries the useful dimensions, expose the complete label.
            matching_name_measure = [
                token
                for token in measure_tokens
                if explicit_size.lower() in token.lower()
            ]
            measure_tokens = matching_name_measure or [explicit_size]
        elif not measure_tokens and _is_measure_label(name):
            measure_tokens = [name]

        for value in measure_tokens:
            if value and value.lower() not in {item.lower() for item in seen_sizes}:
                seen_sizes.add(value)
                sizes.append(value)

        color_tokens = [explicit_color] if explicit_color else []
        if not explicit_color and not _is_measure_label(name):
            color_tokens = name_tokens
        elif not explicit_color:
            color_tokens.extend(token for token in name_tokens if not _is_measure_label(token))
        for token in color_tokens:
            compact = (token or "").strip()
            if not compact or _is_measure_label(compact):
                continue
            title = compact.title()
            if title.lower() not in {item.lower() for item in seen_colors}:
                seen_colors.add(title)
                colors.append(title)

    return sizes, colors


def _variant_attribute(variant: ProductVariant, *keys: str) -> str | None:
    attributes = variant.attributes if isinstance(variant.attributes, dict) else {}
    normalized = {str(key).strip().lower(): value for key, value in attributes.items()}
    for key in keys:
        value = normalized.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _published_unit_price(
    published_product: PublishedProduct,
    product: Product,
    variant: ProductVariant | None,
    pricing: ProductPricing | None = None,
) -> float:
    base_price = pricing.base_price if pricing else float(product.price or 0)
    raw_price = (
        pricing.variant_prices.get(variant.id, float(variant.price) if variant.price is not None else base_price + float(variant.price_extra or 0))
        if variant and pricing
        else float(variant.price) if variant and variant.price is not None
        else float(product.price or 0) + float(variant.price_extra or 0) if variant
        else float(product.price or 0)
    )
    unit_price = _safe_float(published_product.price_override, raw_price)
    if variant and published_product.price_override is not None and base_price:
        unit_price = float(published_product.price_override) + (raw_price - base_price)
    return max(0.0, unit_price)


def _serialize_admin_published_product(published_product: PublishedProduct) -> schemas.PublishedProduct:
    base_price = None
    if published_product.product and published_product.product.price is not None:
        base_price = float(published_product.product.price)

    return schemas.PublishedProduct(
        id=published_product.id,
        storefront_id=published_product.storefront_id,
        product_id=published_product.product_id,
        slug=published_product.slug,
        is_published=published_product.is_published,
        is_featured=published_product.is_featured,
        sort_order=published_product.sort_order,
        seo_title=published_product.seo_title,
        seo_description=published_product.seo_description,
        base_price=base_price,
        product_name=published_product.product.name if published_product.product else None,
        product_description=published_product.product.description if published_product.product else None,
        company_id=published_product.company_id,
        created_at=published_product.created_at,
        updated_at=published_product.updated_at,
        is_active=published_product.is_active,
    )


def _serialize_public_product(
    published_product: PublishedProduct,
    product: Product,
    stock_map: dict[tuple[uuid.UUID, uuid.UUID | None], float] | None = None,
    *,
    compact: bool = False,
    pricing: ProductPricing | None = None,
) -> schemas.PublicProduct:
    title = (published_product.custom_title or product.name or "").strip()
    seo_title = (getattr(published_product, "seo_title", None) or title).strip() or title
    seo_description = None
    if not compact:
        seo_description = (
            getattr(published_product, "seo_description", None)
            or getattr(published_product, "custom_description", None)
            or product.description
            or ""
        ).strip() or None
    # Catalog cards do not render descriptions. Some provider descriptions
    # contain complete HTML galleries, so sending them with every page makes
    # the RSC payload unnecessarily large. Detail pages still receive the
    # complete description through the default ``compact=False`` path.
    description = (
        (published_product.custom_description or product.description or "").strip() or None
        if not compact
        else None
    )
    base_price = pricing.base_price if pricing else float(product.price or 0)
    stock_map = stock_map or {}
    variants: list[schemas.PublicProductVariant] = []
    for variant in product.variants or []:
        variant_price = _published_unit_price(published_product, product, variant, pricing)
        variant_stock = max(0.0, _safe_float(stock_map.get((product.id, variant.id), 0.0)))
        variants.append(
            schemas.PublicProductVariant(
                id=variant.id,
                name=(variant.name or "").strip(),
                sku=variant.sku,
                attributes=variant.attributes if isinstance(variant.attributes, dict) else {},
                price=variant_price,
                compare_at_price=(
                    float(published_product.compare_at_price)
                    if published_product.compare_at_price is not None
                    else None
                ),
                in_stock=not bool(product.track_inventory) or variant_stock > 0,
                stock_quantity=variant_stock if product.track_inventory else None,
            )
        )
    price = min((variant.price for variant in variants), default=_safe_float(published_product.price_override, base_price))
    image_url = published_product.product.image_url or product.image_url
    gallery: list[str] = []
    seen_gallery: set[str] = set()
    for candidate in [image_url, *(img.image_url for img in sorted(product.images or [], key=lambda item: item.order))]:
        normalized_candidate = str(candidate or "").strip()
        candidate_key = normalized_candidate.casefold()
        if normalized_candidate and candidate_key not in seen_gallery:
            seen_gallery.add(candidate_key)
            gallery.append(normalized_candidate)
    if compact:
        # Listing cards only use the primary and hover image. Keep detail
        # responses unchanged while avoiding needless gallery URLs in pages.
        gallery = gallery[:2]
    available_sizes, available_colors = _extract_variant_facets(product.variants or [])
    is_tracked = bool(product.track_inventory)
    if variants:
        available_stock = sum(float(variant.stock_quantity or 0) for variant in variants) if is_tracked else None
    else:
        available_stock = max(0.0, _safe_float(stock_map.get((product.id, None), 0.0))) if is_tracked else None
    return schemas.PublicProduct(
        id=published_product.id,
        product_id=product.id,
        slug=published_product.slug,
        title=title,
        description=description,
        category_name=product.category.name if getattr(product, "category", None) else None,
        brand_name=product.brand.name if getattr(product, "brand", None) else None,
        product_type=product.product_type,
        available_sizes=available_sizes,
        available_colors=available_colors,
        variants=variants,
        image_url=image_url,
        gallery=gallery,
        price=price,
        base_price=base_price,
        compare_at_price=(
            _safe_float(published_product.compare_at_price)
            if published_product.compare_at_price is not None
            else None
        ),
        is_featured=bool(published_product.is_featured),
        show_stock=is_tracked,
        in_stock=not is_tracked or bool(available_stock and available_stock > 0),
        stock_quantity=available_stock,
        seo_title=seo_title,
        seo_description=seo_description,
    )


def _public_product_starting_price(
    published_product: PublishedProduct,
    product: Product,
    pricing: ProductPricing | None = None,
) -> float:
    """Return the lowest sellable variant price used by catalog filters/sort."""
    base_price = pricing.base_price if pricing else float(product.price or 0)
    if not product.variants:
        return _safe_float(published_product.price_override, base_price)
    prices = [_published_unit_price(published_product, product, variant, pricing) for variant in product.variants]
    return min(prices, default=_safe_float(published_product.price_override, base_price))


def _normalize_catalog_sort(value: str | None) -> str:
    normalized = (value or "latest").strip().lower()
    allowed = {"latest", "best-selling", "price-low", "price-high", "oldest"}
    return normalized if normalized in allowed else "latest"


def _normalize_catalog_text(value: str | None) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFD", value or "") if unicodedata.category(char) != "Mn"
    ).lower()


def _normalize_product_type_label(value: str | None) -> str:
    if not value:
        return "Otro"
    return " ".join(part.capitalize() for part in str(value).lower().split("_"))


def _parse_multi_query_param(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def _parse_uuid_query_list(value: str | None, limit: int = 24) -> list[uuid.UUID]:
    parsed: list[uuid.UUID] = []
    for item in _parse_multi_query_param(value):
        try:
            candidate = uuid.UUID(item)
        except (ValueError, AttributeError):
            continue
        if candidate not in parsed:
            parsed.append(candidate)
        if len(parsed) >= limit:
            break
    return parsed


async def _get_public_storefront_by_id(
    db: AsyncSession,
    storefront_id: uuid.UUID,
    preview_token: str | None = None,
) -> Storefront:
    preview_claims = auth.get_storefront_preview_claims(preview_token) if preview_token else None
    preview_storefront_id = preview_claims[0] if preview_claims else None
    preview_company_id = preview_claims[1] if preview_claims else None
    result = await db.execute(
        select(Storefront).where(
            Storefront.id == storefront_id,
            Storefront.is_active == True,
            or_(
                Storefront.is_enabled == True,
                and_(
                    Storefront.id == preview_storefront_id,
                    Storefront.company_id == preview_company_id,
                ),
            ),
        )
    )
    storefront = result.scalars().first()
    if not storefront:
        raise HTTPException(status_code=404, detail="Storefront not found")
    return storefront


async def _get_public_storefront_by_subdomain(
    db: AsyncSession,
    subdomain: str,
    preview_token: str | None = None,
) -> Storefront:
    normalized_subdomain = subdomain.strip().lower()
    if not normalized_subdomain:
        raise HTTPException(status_code=404, detail="Storefront not found")

    preview_claims = auth.get_storefront_preview_claims(preview_token) if preview_token else None
    preview_storefront_id = preview_claims[0] if preview_claims else None
    preview_company_id = preview_claims[1] if preview_claims else None
    result = await db.execute(
        select(Storefront).where(
            Storefront.subdomain == normalized_subdomain,
            Storefront.is_active == True,
            or_(
                Storefront.is_enabled == True,
                and_(
                    Storefront.id == preview_storefront_id,
                    Storefront.company_id == preview_company_id,
                ),
            ),
        )
    )
    storefront = result.scalars().first()
    if not storefront:
        raise HTTPException(status_code=404, detail="Storefront not found")
    return storefront


async def _get_public_storefront_by_domain(
    db: AsyncSession,
    domain: str,
    preview_token: str | None = None,
) -> Storefront:
    normalized_domain = domain.strip().lower().split(":", 1)[0]
    if not normalized_domain:
        raise HTTPException(status_code=404, detail="Storefront not found")

    preview_claims = auth.get_storefront_preview_claims(preview_token) if preview_token else None
    preview_storefront_id = preview_claims[0] if preview_claims else None
    preview_company_id = preview_claims[1] if preview_claims else None
    result = await db.execute(
        select(Storefront)
        .join(StorefrontDomain, StorefrontDomain.storefront_id == Storefront.id)
        .where(
            StorefrontDomain.domain == normalized_domain,
            StorefrontDomain.is_active == True,
            StorefrontDomain.is_verified == True,
            Storefront.is_active == True,
            or_(
                Storefront.is_enabled == True,
                and_(
                    Storefront.id == preview_storefront_id,
                    Storefront.company_id == preview_company_id,
                ),
            ),
        )
    )
    storefront = result.scalars().first()
    if not storefront:
        raise HTTPException(status_code=404, detail="Storefront not found")
    return storefront


async def _get_storefront_for_certificate_by_subdomain(
    db: AsyncSession,
    subdomain: str,
) -> Storefront:
    """Authorize TLS for known active stores, including unpublished previews."""
    normalized_subdomain = subdomain.strip().lower()
    result = await db.execute(
        select(Storefront).where(
            Storefront.subdomain == normalized_subdomain,
            Storefront.is_active == True,
        )
    )
    storefront = result.scalars().first()
    if not storefront:
        raise HTTPException(status_code=404, detail="Unknown storefront")
    return storefront


async def _get_storefront_for_certificate_by_domain(
    db: AsyncSession,
    domain: str,
) -> Storefront:
    """Authorize TLS only for a verified domain owned by an active store."""
    normalized_domain = domain.strip().lower().split(":", 1)[0]
    result = await db.execute(
        select(Storefront)
        .join(StorefrontDomain, StorefrontDomain.storefront_id == Storefront.id)
        .where(
            StorefrontDomain.domain == normalized_domain,
            StorefrontDomain.is_active == True,
            StorefrontDomain.is_verified == True,
            Storefront.is_active == True,
        )
    )
    storefront = result.scalars().first()
    if not storefront:
        raise HTTPException(status_code=404, detail="Unknown storefront")
    return storefront


async def _get_public_collection_or_404(
    db: AsyncSession,
    storefront_id: uuid.UUID,
    slug: str,
    preview_token: str | None = None,
) -> StoreCollection:
    await _get_public_storefront_by_id(db, storefront_id, preview_token)
    result = await db.execute(
        select(StoreCollection).where(
            StoreCollection.storefront_id == storefront_id,
            StoreCollection.slug == slug,
            StoreCollection.is_active == True,
            StoreCollection.is_visible == True,
        )
    )
    collection = result.scalars().first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


async def _get_public_published_product_or_404(
    db: AsyncSession,
    storefront_id: uuid.UUID,
    slug: str,
    preview_token: str | None = None,
) -> PublishedProduct:
    result = await db.execute(
        select(PublishedProduct)
        .options(
            selectinload(PublishedProduct.product).selectinload(Product.images),
            selectinload(PublishedProduct.product).selectinload(Product.category),
            selectinload(PublishedProduct.product).selectinload(Product.brand),
            selectinload(PublishedProduct.product).selectinload(Product.variants),
        )
        .where(
            PublishedProduct.storefront_id == storefront_id,
            PublishedProduct.slug == slug,
            PublishedProduct.is_active == True,
            PublishedProduct.is_published == True,
        )
    )
    published_product = result.scalars().first()
    if not published_product or not published_product.product:
        raise HTTPException(status_code=404, detail="Product not found")
    storefront = await _get_public_storefront_by_id(db, storefront_id, preview_token)
    stock_map = await _get_storefront_stock_map(db, storefront, [published_product.product_id])
    if not _public_product_has_available_stock(published_product.product, stock_map):
        raise HTTPException(status_code=404, detail="Product not found")
    return published_product


async def _get_storefront_or_404(db: AsyncSession, storefront_id: uuid.UUID, company_id: uuid.UUID) -> Storefront:
    result = await db.execute(
        select(Storefront).where(
            Storefront.id == storefront_id,
            Storefront.company_id == company_id,
            Storefront.is_active == True,
        )
    )
    storefront = result.scalars().first()
    if not storefront:
        raise HTTPException(status_code=404, detail="Storefront not found")
    return storefront


def _theme_template_or_422(template_key: str) -> str:
    try:
        return validate_template_key(template_key)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _normalize_theme_document(
    template_key: str,
    document: Any,
    theme_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if template_key == "product":
        normalizer = normalize_product_document
    elif template_key == "cart":
        normalizer = normalize_cart_document
    elif template_key == "pages":
        normalizer = normalize_pages_document
    elif template_key == "collection":
        normalizer = normalize_collection_document
    elif template_key == "search":
        normalizer = normalize_search_document
    else:
        normalizer = normalize_home_document
    return normalizer(document, theme_settings)


def _storefront_preview_url(storefront: Storefront) -> str | None:
    platform_domain, platform_port = _platform_storefront_host_and_port()
    subdomain = (storefront.subdomain or "").strip().lower().strip(".")
    if (
        not platform_domain
        or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", subdomain)
    ):
        return None
    scheme = "http" if platform_domain in {"localhost", "127.0.0.1"} else "https"
    port_suffix = f":{platform_port}" if platform_port else ""
    return f"{scheme}://{subdomain}.{platform_domain}{port_suffix}/"


def _create_storefront_theme_preview_session(
    storefront: Storefront,
    user_id: uuid.UUID,
    template_key: str = "home",
) -> tuple[str, datetime]:
    expires_delta = timedelta(minutes=15)
    expires_at = datetime.now(timezone.utc) + expires_delta
    token = auth.create_access_token(
        data={
            "sub": str(user_id),
            "scope": "storefront_theme_preview",
            "storefront_id": str(storefront.id),
            "company_id": str(storefront.company_id),
            "template_key": template_key,
            "jti": secrets.token_urlsafe(16),
        },
        expires_delta=expires_delta,
    )
    return token, expires_at


async def _get_theme_document(
    db: AsyncSession,
    storefront: Storefront,
    template_key: str,
    create: bool = False,
    user_id: uuid.UUID | None = None,
    lock: bool = False,
) -> StorefrontThemeDocumentModel | None:
    query = select(StorefrontThemeDocumentModel).where(
        StorefrontThemeDocumentModel.storefront_id == storefront.id,
        StorefrontThemeDocumentModel.company_id == storefront.company_id,
        StorefrontThemeDocumentModel.template_key == template_key,
        StorefrontThemeDocumentModel.is_active == True,
    )
    if lock:
        query = query.with_for_update()
    document = await db.scalar(query)
    if document or not create:
        return document

    if template_key == "product":
        initial = build_product_document(storefront.theme_settings)
    elif template_key == "cart":
        initial = build_cart_document(storefront.theme_settings)
    elif template_key == "pages":
        initial = build_pages_document(storefront.theme_settings)
    elif template_key == "collection":
        initial = build_collection_document(storefront.theme_settings)
    elif template_key == "search":
        initial = build_search_document(storefront.theme_settings)
    else:
        initial = build_home_document(storefront.theme_settings)
    document = StorefrontThemeDocumentModel(
        storefront_id=storefront.id,
        company_id=storefront.company_id,
        template_key=template_key,
        draft_document=initial,
        published_document=initial,
        draft_version=1,
        published_version=1,
        published_at=datetime.now(timezone.utc),
        published_by_id=user_id,
        created_by_id=user_id,
        updated_by_id=user_id,
    )
    db.add(document)
    await db.flush()
    return document


def _serialize_storefront_media_asset(asset: StorefrontMediaAsset) -> schemas.StorefrontMediaAsset:
    return schemas.StorefrontMediaAsset(
        id=asset.id,
        storefront_id=asset.storefront_id,
        company_id=asset.company_id,
        url=asset.storage_path,
        original_filename=asset.original_filename,
        content_type=asset.content_type,
        size_bytes=asset.size_bytes,
        width=asset.width,
        height=asset.height,
        alt_text=asset.alt_text,
        created_at=asset.created_at,
    )


def _safe_media_filename(value: str | None, fallback: str) -> str:
    candidate = Path(value or "").name
    candidate = re.sub(r"[\x00-\x1f\x7f]", "", candidate).strip()
    return (candidate or fallback)[:255]


async def _validate_theme_references(
    db: AsyncSession,
    storefront: Storefront,
    document: dict[str, Any],
) -> None:
    """Ensure visual selectors cannot reference another tenant's catalog."""
    collection_ids: set[uuid.UUID] = set()
    product_ids: set[uuid.UUID] = set()
    for section in document.get("sections", []):
        if not isinstance(section, dict):
            continue
        settings = section.get("settings")
        if not isinstance(settings, dict):
            continue
        for field_name, target in (("collection_ids", collection_ids), ("product_ids", product_ids)):
            values = settings.get(field_name, [])
            if values is None:
                continue
            if not isinstance(values, list) or len(values) > 24:
                raise ValueError(f"La selección {field_name} debe contener como máximo 24 IDs.")
            for value in values:
                try:
                    target.add(uuid.UUID(str(value)))
                except (ValueError, TypeError, AttributeError) as exc:
                    raise ValueError(f"La selección {field_name} contiene un ID inválido.") from exc

    if collection_ids:
        result = await db.execute(
            select(StoreCollection.id).where(
                StoreCollection.id.in_(collection_ids),
                StoreCollection.storefront_id == storefront.id,
                StoreCollection.company_id == storefront.company_id,
                StoreCollection.is_active == True,
                StoreCollection.is_visible == True,
            )
        )
        missing = collection_ids - set(result.scalars().all())
        if missing:
            raise ValueError("Una o más colecciones no pertenecen a esta tienda o ya no están disponibles.")

    if product_ids:
        result = await db.execute(
            select(PublishedProduct.id).where(
                PublishedProduct.id.in_(product_ids),
                PublishedProduct.storefront_id == storefront.id,
                PublishedProduct.company_id == storefront.company_id,
                PublishedProduct.is_active == True,
                PublishedProduct.is_published == True,
            )
        )
        missing = product_ids - set(result.scalars().all())
        if missing:
            raise ValueError("Uno o más productos no pertenecen a esta tienda o ya no están publicados.")


def _serialize_theme_document(
    document: StorefrontThemeDocumentModel,
    theme_settings: dict[str, Any] | None,
    storefront: Storefront | None = None,
) -> schemas.StorefrontThemeDocument:
    if document.template_key == "product":
        normalizer = normalize_product_document
    elif document.template_key == "cart":
        normalizer = normalize_cart_document
    elif document.template_key == "pages":
        normalizer = normalize_pages_document
    elif document.template_key == "collection":
        normalizer = normalize_collection_document
    elif document.template_key == "search":
        normalizer = normalize_search_document
    else:
        normalizer = normalize_home_document
    return schemas.StorefrontThemeDocument(
        id=document.id,
        storefront_id=document.storefront_id,
        company_id=document.company_id,
        template_key=document.template_key,
        draft_document=normalizer(document.draft_document, theme_settings),
        published_document=normalizer(document.published_document, theme_settings),
        draft_version=document.draft_version,
        published_version=document.published_version,
        published_at=document.published_at,
        preview_url=_storefront_preview_url(storefront) if storefront else None,
    )


async def _published_theme_document(
    db: AsyncSession,
    storefront: Storefront,
    template_key: str = "home",
) -> dict[str, Any]:
    document = await _get_theme_document(db, storefront, template_key)
    if not document:
        if template_key == "product":
            return build_product_document(storefront.theme_settings)
        if template_key == "cart":
            return build_cart_document(storefront.theme_settings)
        if template_key == "pages":
            return build_pages_document(storefront.theme_settings)
        if template_key == "collection":
            return build_collection_document(storefront.theme_settings)
        if template_key == "search":
            return build_search_document(storefront.theme_settings)
        return build_home_document(storefront.theme_settings)
    if template_key == "product":
        normalizer = normalize_product_document
    elif template_key == "cart":
        normalizer = normalize_cart_document
    elif template_key == "pages":
        normalizer = normalize_pages_document
    elif template_key == "collection":
        normalizer = normalize_collection_document
    elif template_key == "search":
        normalizer = normalize_search_document
    else:
        normalizer = normalize_home_document
    return normalizer(document.published_document, storefront.theme_settings)


async def _published_theme_documents(
    db: AsyncSession,
    storefront: Storefront,
) -> dict[str, dict[str, Any]]:
    return {
        "home": await _published_theme_document(db, storefront, "home"),
        "product": await _published_theme_document(db, storefront, "product"),
        "cart": await _published_theme_document(db, storefront, "cart"),
        "pages": await _published_theme_document(db, storefront, "pages"),
        "collection": await _published_theme_document(db, storefront, "collection"),
        "search": await _published_theme_document(db, storefront, "search"),
    }


async def _validate_storefront_price_list(db: AsyncSession, price_list_id: uuid.UUID | None, company_id: uuid.UUID) -> None:
    if not price_list_id:
        return
    price_list = await db.scalar(
        select(PriceList).where(
            PriceList.id == price_list_id,
            PriceList.company_id == company_id,
            PriceList.type == "SALE",
            PriceList.is_active.is_(True),
        )
    )
    if not price_list:
        raise HTTPException(status_code=400, detail="La lista seleccionada debe ser una lista de venta activa")


async def _get_collection_or_404(db: AsyncSession, collection_id: uuid.UUID, company_id: uuid.UUID) -> StoreCollection:
    result = await db.execute(
        select(StoreCollection).where(
            StoreCollection.id == collection_id,
            StoreCollection.company_id == company_id,
            StoreCollection.is_active == True,
        )
    )
    collection = result.scalars().first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


async def _get_published_product_or_404(db: AsyncSession, published_product_id: uuid.UUID, company_id: uuid.UUID) -> PublishedProduct:
    result = await db.execute(
        select(PublishedProduct).where(
            PublishedProduct.id == published_product_id,
            PublishedProduct.company_id == company_id,
            PublishedProduct.is_active == True,
        )
    )
    published_product = result.scalars().first()
    if not published_product:
        raise HTTPException(status_code=404, detail="Published product not found")
    return published_product


async def _get_navigation_item_or_404(db: AsyncSession, navigation_item_id: uuid.UUID, company_id: uuid.UUID) -> StoreNavigationItem:
    result = await db.execute(
        select(StoreNavigationItem).where(
            StoreNavigationItem.id == navigation_item_id,
            StoreNavigationItem.company_id == company_id,
            StoreNavigationItem.is_active == True,
        )
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Navigation item not found")
    return item


async def _deactivate_navigation_branch(db: AsyncSession, item: StoreNavigationItem, user_id: uuid.UUID) -> None:
    result = await db.execute(
        select(StoreNavigationItem).where(
            StoreNavigationItem.parent_id == item.id,
            StoreNavigationItem.is_active == True,
        )
    )
    children = result.scalars().all()
    for child in children:
        await _deactivate_navigation_branch(db, child, user_id)

    item.is_active = False
    item.updated_by_id = user_id
    db.add(item)


async def _get_payment_gateway_or_404(db: AsyncSession, gateway_id: uuid.UUID, company_id: uuid.UUID) -> StorePaymentGateway:
    result = await db.execute(
        select(StorePaymentGateway).where(
            StorePaymentGateway.id == gateway_id,
            StorePaymentGateway.company_id == company_id,
            StorePaymentGateway.is_active == True,
        )
    )
    gateway = result.scalars().first()
    if not gateway:
        raise HTTPException(status_code=404, detail="Payment gateway not found")
    return gateway


async def _get_enabled_gateway_for_storefront(
    db: AsyncSession,
    storefront_id: uuid.UUID,
    provider: str,
) -> StorePaymentGateway:
    result = await db.execute(
        select(StorePaymentGateway).where(
            StorePaymentGateway.storefront_id == storefront_id,
            StorePaymentGateway.provider == provider,
            StorePaymentGateway.is_active == True,
            StorePaymentGateway.is_enabled == True,
        )
    )
    gateway = result.scalars().first()
    if not gateway:
        raise HTTPException(status_code=400, detail=f"Payment provider '{provider}' is not active for this storefront")
    if gateway.provider not in SUPPORTED_PUBLIC_PAYMENT_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Payment provider '{provider}' is not available for checkout")
    return gateway


def _serialize_admin_payment_gateway(gateway: StorePaymentGateway) -> schemas.StorePaymentGateway:
    """Never return private gateway credentials to the Angular administration UI."""
    response = schemas.StorePaymentGateway.model_validate(gateway)
    response.secret_key_encrypted = None
    response.extra_config = {
        key: value
        for key, value in (gateway.extra_config or {}).items()
        if key.lower() not in SENSITIVE_GATEWAY_CONFIG_KEYS
    }
    return response


def _gateway_checkout_flow(provider: str, extra_config: dict | None = None) -> str:
    if provider in {"manual_transfer", "cod"}:
        return "manual"
    if provider == "whatsapp":
        return "whatsapp"
    if provider == "wompi":
        return "form_redirect"
    return "external_redirect"


def _validate_payment_gateway_provider(provider: str) -> str:
    normalized = (provider or "").strip().lower()
    if normalized not in SUPPORTED_PUBLIC_PAYMENT_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported payment provider.",
        )
    return normalized


def _validate_gateway_checkout_configuration(gateway: StorePaymentGateway) -> None:
    """Fail before creating an order when an enabled provider is incomplete."""
    config = gateway.extra_config or {}
    if gateway.provider == "whatsapp":
        number = "".join(char for char in str(config.get("whatsapp_number") or "") if char.isdigit())
        if len(number) < 8:
            raise HTTPException(status_code=400, detail="Configura el número de WhatsApp antes de activar esta forma de pago")
    elif gateway.provider == "addi":
        has_credentials = bool(gateway.public_key and gateway.secret_key_encrypted)
        if has_credentials:
            required = ("callback_url", "callback_username", "callback_password")
            if not all(str(config.get(key) or "").strip() for key in required):
                raise HTTPException(
                    status_code=400,
                    detail="Configura callback URL y credenciales de notificación de Addi antes de activarla",
                )
        elif not gateway.is_sandbox:
            raise HTTPException(
                status_code=400,
                detail="Configura Client ID y Client secret de Addi antes de activar esta forma de pago",
            )
    elif gateway.provider == "sistecredito":
        if not str(config.get("checkout_url") or "").strip().startswith("https://"):
            if gateway.is_sandbox:
                return
            raise HTTPException(
                status_code=400,
                detail=f"Configura la URL segura de checkout de {gateway.display_name} antes de activarla",
            )


async def _resolve_default_branch_for_company(db: AsyncSession, company_id: uuid.UUID) -> Branch:
    result = await db.execute(
        select(Branch).where(
            Branch.company_id == company_id,
            Branch.is_active == True,
            Branch.allow_pos == True,
        ).order_by(Branch.created_at.asc())
    )
    branch = result.scalars().first()
    if not branch:
        raise HTTPException(status_code=400, detail="No active branch available to register ecommerce orders")
    return branch


async def _get_storefront_stock_map(
    db: AsyncSession,
    storefront: Storefront,
    product_ids: list[uuid.UUID],
    warehouse: Warehouse | None = None,
) -> dict[tuple[uuid.UUID, uuid.UUID | None], float]:
    if not product_ids:
        return {}
    warehouse = warehouse or await _resolve_storefront_fulfillment_warehouse(db, storefront)
    result = await db.execute(
        select(Inventory.product_id, Inventory.variant_id, Inventory.quantity, Inventory.reserved_quantity).where(
            Inventory.warehouse_id == warehouse.id,
            Inventory.product_id.in_(product_ids),
        )
    )
    stock: dict[tuple[uuid.UUID, uuid.UUID | None], float] = {}
    for product_id, variant_id, quantity, reserved_quantity in result.all():
        key = (product_id, variant_id)
        stock[key] = stock.get(key, 0.0) + max(0.0, _safe_float(quantity) - _safe_float(reserved_quantity))
    return stock


def _public_product_has_available_stock(
    product: Product | None,
    stock_map: dict[tuple[uuid.UUID, uuid.UUID | None], float],
) -> bool:
    """Return whether a product is sellable in the storefront warehouse.

    Products that do not track inventory (for example services) remain
    available. Tracked products need a positive available quantity in at
    least one product/variant inventory row; reserved quantities are already
    deducted by ``_get_storefront_stock_map``.
    """
    if not product or not product.track_inventory:
        return bool(product)
    return any(
        product_id == product.id and quantity > 0
        for (product_id, _variant_id), quantity in stock_map.items()
    )


async def _resolve_storefront_fulfillment_warehouse(db: AsyncSession, storefront: Storefront) -> Warehouse:
    if not storefront.fulfillment_warehouse_id:
        raise HTTPException(status_code=400, detail="Configura una bodega de fulfillment para la tienda")
    warehouse = await db.scalar(
        select(Warehouse).join(Branch).where(
            Warehouse.id == storefront.fulfillment_warehouse_id,
            Warehouse.is_active == True,
            Warehouse.allows_ecommerce == True,
            Branch.company_id == storefront.company_id,
        )
    )
    if not warehouse:
        raise HTTPException(status_code=400, detail="La bodega de fulfillment de la tienda no está disponible")
    return warehouse


async def _resolve_default_user_for_company(db: AsyncSession, company_id: uuid.UUID) -> User:
    result = await db.execute(
        select(User).where(
            User.company_id == company_id,
            User.is_active == True,
            or_(User.role_id.is_not(None), User.is_superuser == True),
        ).order_by(User.created_at.asc())
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=400, detail="No active user available to register ecommerce orders")
    return user


async def _load_checkout_products(
    db: AsyncSession,
    storefront_id: uuid.UUID,
    items: list[schemas.PublicCheckoutItemInput],
) -> tuple[list[schemas.PublicCheckoutPreviewItem], float]:
    if not items:
        raise HTTPException(status_code=400, detail="At least one item is required")

    merged: dict[tuple[uuid.UUID, uuid.UUID | None], float] = {}
    for item in items:
        if item.quantity <= 0:
            raise HTTPException(status_code=400, detail="Item quantity must be greater than zero")
        key = (item.published_product_id, item.variant_id)
        merged[key] = merged.get(key, 0.0) + float(item.quantity)

    published_ids = list({published_id for published_id, _variant_id in merged})
    result = await db.execute(
        select(PublishedProduct)
        .options(
            selectinload(PublishedProduct.product),
            selectinload(PublishedProduct.product).selectinload(Product.category),
            selectinload(PublishedProduct.product).selectinload(Product.brand),
            selectinload(PublishedProduct.product).selectinload(Product.variants),
        )
        .where(
            PublishedProduct.storefront_id == storefront_id,
            PublishedProduct.id.in_(published_ids),
            PublishedProduct.is_active == True,
            PublishedProduct.is_published == True,
        )
    )
    published_map: dict[uuid.UUID, PublishedProduct] = {item.id: item for item in result.scalars().all()}

    if len(published_map) != len(published_ids):
        raise HTTPException(status_code=400, detail="One or more products are not available in this storefront")

    price_list_id = await db.scalar(select(Storefront.price_list_id).where(Storefront.id == storefront_id))
    pricing_context = await load_price_list_context(
        db,
        price_list_id,
        [published.product_id for published in published_map.values()],
    )

    rows: list[schemas.PublicCheckoutPreviewItem] = []
    subtotal = 0.0
    for (published_id, variant_id), quantity in merged.items():
        published = published_map[published_id]
        product = published.product
        if not product:
            raise HTTPException(status_code=400, detail="One or more products are not available")
        variant = None
        if variant_id:
            variant = next((entry for entry in product.variants or [] if entry.id == variant_id), None)
            if not variant:
                raise HTTPException(status_code=400, detail=f"La variante seleccionada no pertenece a '{product.name}'")
        elif product.variants:
            # A product with exactly one variant is unambiguous. Older carts
            # may not have persisted its variant id, so resolve that legacy
            # entry instead of blocking checkout. Products with multiple
            # options still require an explicit customer selection.
            if len(product.variants) == 1:
                variant = product.variants[0]
                variant_id = variant.id
            else:
                raise HTTPException(status_code=400, detail=f"Selecciona una variante para '{product.name}'")
        pricing = resolve_product_pricing(pricing_context, product)
        unit_price = _published_unit_price(published, product, variant, pricing)
        line_subtotal = unit_price * quantity
        subtotal += line_subtotal
        rows.append(
            schemas.PublicCheckoutPreviewItem(
                published_product_id=published.id,
                product_id=product.id,
                variant_id=variant_id,
                slug=published.slug,
                title=(product.name or "").strip(),
                variant_name=variant.name if variant else None,
                quantity=quantity,
                unit_price=unit_price,
                line_subtotal=line_subtotal,
            )
        )

    return rows, subtotal


async def _validate_checkout_inventory(
    db: AsyncSession,
    warehouse_id: uuid.UUID,
    rows: list[schemas.PublicCheckoutPreviewItem],
) -> None:
    """Prevent a storefront draft from being created for unavailable physical stock."""
    for row in rows:
        product_result = await db.execute(select(Product).where(Product.id == row.product_id))
        product = product_result.scalars().first()
        if not product or not product.track_inventory:
            continue

        inventory_query = select(Inventory.quantity, Inventory.reserved_quantity).where(
            Inventory.product_id == product.id,
            Inventory.warehouse_id == warehouse_id,
        )
        if row.variant_id:
            inventory_query = inventory_query.where(Inventory.variant_id == row.variant_id)
        else:
            inventory_query = inventory_query.where(Inventory.variant_id.is_(None))
        inventory_result = await db.execute(inventory_query)
        inventory_row = inventory_result.one_or_none()
        available = (_safe_float(inventory_row[0]) - _safe_float(inventory_row[1])) if inventory_row else 0.0
        if available < row.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente para '{row.title}'. Disponible: {available:g}",
            )


async def _tracked_sale_items(db: AsyncSession, sale: Sale) -> list[tuple[SaleItem, Product]]:
    """Return tracked sale items without triggering async-incompatible lazy loads."""
    # A newly-created sale and eagerly-loaded sales already carry this
    # relationship in memory. Only query when SQLAlchemy left it unloaded.
    sale_items = sale.__dict__.get("items")
    if sale_items is None:
        result = await db.execute(
            select(SaleItem)
            .options(selectinload(SaleItem.product), selectinload(SaleItem.variant))
            .where(SaleItem.sale_id == sale.id)
        )
        sale_items = result.scalars().all()

    unresolved_product_ids = {
        item.product_id
        for item in sale_items
        if item.__dict__.get("product") is None
    }
    products: dict[uuid.UUID, Product] = {}
    if unresolved_product_ids:
        result = await db.execute(select(Product).where(Product.id.in_(unresolved_product_ids)))
        products = {product.id: product for product in result.scalars().all()}

    tracked_items: list[tuple[SaleItem, Product]] = []
    for item in sale_items:
        product = item.__dict__.get("product") or products.get(item.product_id)
        if product and product.track_inventory:
            tracked_items.append((item, product))
    return tracked_items


async def _reserve_storefront_sale(db: AsyncSession, sale: Sale) -> bool:
    """Confirm an ecommerce order and reserve its inventory exactly once."""
    # Payment providers can retry status callbacks long after operations has
    # started picking or dispatching the order.  Those retries must be safe:
    # inventory was already reserved at confirmation and the order remains a
    # valid order, not a stock failure.
    if sale.status in {
        SaleStatus.CONFIRMED,
        SaleStatus.PICKING,
        SaleStatus.PACKING,
        SaleStatus.DISPATCHED,
        SaleStatus.DELIVERED,
        SaleStatus.COMPLETED,
    }:
        return True
    if sale.status not in {SaleStatus.DRAFT, SaleStatus.QUOTE}:
        return False

    tracked_items = await _tracked_sale_items(db, sale)
    requested_by_product: dict[tuple[uuid.UUID, uuid.UUID | None], float] = {}
    for item, _product in tracked_items:
        key = (item.product_id, getattr(item, "variant_id", None))
        requested_by_product[key] = requested_by_product.get(key, 0.0) + item.quantity

    inventories: dict[tuple[uuid.UUID, uuid.UUID | None], Inventory] = {}
    for (product_id, variant_id), requested_quantity in requested_by_product.items():
        result = await db.execute(
            select(Inventory)
            .where(
                Inventory.product_id == product_id,
                Inventory.warehouse_id == sale.warehouse_id,
                Inventory.variant_id == variant_id if variant_id else Inventory.variant_id.is_(None),
            )
            .with_for_update()
        )
        inventory = result.scalars().first()
        available = (inventory.quantity - inventory.reserved_quantity) if inventory else 0
        if available < requested_quantity:
            return False
        inventories[(product_id, variant_id)] = inventory

    for item, _product in tracked_items:
        inventory = inventories[(item.product_id, getattr(item, "variant_id", None))]
        inventory.reserved_quantity += item.quantity
        db.add(InventoryMovement(
            product_id=item.product_id,
            variant_id=getattr(item, "variant_id", None),
            branch_id=sale.branch_id,
            warehouse_id=sale.warehouse_id,
            user_id=sale.user_id,
            type=MovementType.RESERVE,
            quantity=0.0,
            previous_stock=inventory.quantity,
            new_stock=inventory.quantity,
            unit_cost=inventory.average_cost,
            reference_id=str(sale.id),
            reason=f"Reserva ecommerce confirmada ({item.quantity:g} unidades)",
            company_id=sale.company_id,
        ))

    previous_status = sale.status
    sale.status = SaleStatus.CONFIRMED
    await log_sale_event(
        db,
        sale_id=str(sale.id),
        company_id=str(sale.company_id),
        event_type="SALE_STATUS_CHANGED",
        title="Orden confirmada",
        description="La orden fue confirmada y quedó lista para preparación.",
        status="success",
        metadata={"from": previous_status.value, "to": SaleStatus.CONFIRMED.value},
    )
    await log_sale_event(
        db,
        sale_id=str(sale.id),
        company_id=str(sale.company_id),
        event_type="INVENTORY_RESERVED",
        title="Inventario reservado",
        description="El inventario quedó reservado para esta orden.",
        status="success",
        metadata={"warehouse_id": str(sale.warehouse_id)},
    )
    enqueue_outbox_event(
        db,
        event_type="inventory.reserved",
        aggregate_type="sale",
        aggregate_id=sale.id,
        company_id=sale.company_id,
        payload={"sale_id": str(sale.id), "warehouse_id": str(sale.warehouse_id), "source": "storefront"},
    )
    return True


async def _cancel_storefront_sale_and_release_reservation(
    db: AsyncSession,
    sale: Sale,
) -> bool:
    """Cancel a checkout sale and release any reservation made at checkout."""
    previous_status = sale.status
    if sale.status in {SaleStatus.DRAFT, SaleStatus.QUOTE}:
        sale.status = SaleStatus.CANCELLED
        await log_sale_event(
            db,
            sale_id=str(sale.id),
            company_id=str(sale.company_id),
            event_type="SALE_STATUS_CHANGED",
            title="Orden cancelada",
            description="La orden fue cancelada por el estado del pago.",
            status="warning",
            metadata={"from": previous_status.value, "to": SaleStatus.CANCELLED.value},
        )
        return True
    if sale.status != SaleStatus.CONFIRMED:
        return False

    tracked_items = await _tracked_sale_items(db, sale)
    requested_by_product: dict[tuple[uuid.UUID, uuid.UUID | None], float] = {}
    for item, _product in tracked_items:
        key = (item.product_id, getattr(item, "variant_id", None))
        requested_by_product[key] = requested_by_product.get(key, 0.0) + item.quantity

    inventories: dict[tuple[uuid.UUID, uuid.UUID | None], Inventory] = {}
    for (product_id, variant_id), requested_quantity in requested_by_product.items():
        result = await db.execute(
            select(Inventory)
            .where(
                Inventory.product_id == product_id,
                Inventory.warehouse_id == sale.warehouse_id,
                Inventory.variant_id == variant_id if variant_id else Inventory.variant_id.is_(None),
            )
            .with_for_update()
        )
        inventory = result.scalars().first()
        if not inventory or inventory.reserved_quantity < requested_quantity:
            return False
        inventories[(product_id, variant_id)] = inventory

    for (product_id, variant_id), requested_quantity in requested_by_product.items():
        inventory = inventories[(product_id, variant_id)]
        inventory.reserved_quantity -= requested_quantity
        db.add(InventoryMovement(
            product_id=product_id,
            variant_id=variant_id,
            branch_id=sale.branch_id,
            warehouse_id=sale.warehouse_id,
            user_id=sale.user_id,
            type=MovementType.RELEASE,
            quantity=0.0,
            previous_stock=inventory.quantity,
            new_stock=inventory.quantity,
            unit_cost=inventory.average_cost,
            reference_id=str(sale.id),
            reason=f"Reserva ecommerce liberada ({requested_quantity:g} unidades)",
            company_id=sale.company_id,
        ))

    sale.status = SaleStatus.CANCELLED
    await log_sale_event(
        db,
        sale_id=str(sale.id),
        company_id=str(sale.company_id),
        event_type="SALE_STATUS_CHANGED",
        title="Orden cancelada",
        description="La orden fue cancelada por el estado del pago.",
        status="warning",
        metadata={"from": previous_status.value, "to": SaleStatus.CANCELLED.value},
    )
    await log_sale_event(
        db,
        sale_id=str(sale.id),
        company_id=str(sale.company_id),
        event_type="INVENTORY_RELEASED",
        title="Inventario liberado",
        description="La reserva de inventario fue liberada al cancelar la orden.",
        status="warning",
    )
    enqueue_outbox_event(
        db,
        event_type="inventory.released",
        aggregate_type="sale",
        aggregate_id=sale.id,
        company_id=sale.company_id,
        payload={"sale_id": str(sale.id), "warehouse_id": str(sale.warehouse_id), "source": "storefront"},
    )
    return True


def _read_wompi_event_property(data: dict[str, Any], path: str) -> Any:
    """Read a dynamic Wompi signature property relative to the event data."""
    current: Any = data
    parts = [part for part in (path or "").split(".") if part]
    if parts and parts[0] == "data":
        parts = parts[1:]
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _has_valid_wompi_event_signature(
    event: dict[str, Any],
    events_secret: str | None,
    provided_checksum: str | None = None,
) -> bool:
    """Validate Wompi's dynamic SHA256 event checksum without fixed fields."""
    signature = event.get("signature") if isinstance(event.get("signature"), dict) else {}
    properties = signature.get("properties") if isinstance(signature.get("properties"), list) else []
    checksum = provided_checksum or signature.get("checksum")
    timestamp = event.get("timestamp")
    if not events_secret or not properties or not checksum or timestamp is None:
        return False

    values: list[str] = []
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    for property_path in properties:
        value = _read_wompi_event_property(data, str(property_path))
        if value is None:
            return False
        values.append(str(value))
    expected = hashlib.sha256(("".join(values) + str(timestamp) + events_secret).encode("utf-8")).hexdigest()
    return hmac.compare_digest(expected.lower(), str(checksum).strip().lower())


@router.get("/", response_model=List[schemas.Storefront])
async def read_storefronts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    result = await db.execute(
        select(Storefront).where(
            Storefront.company_id == current_user.company_id,
            Storefront.is_active == True,
        ).order_by(Storefront.created_at.asc())
    )
    return result.scalars().all()


@router.post("/", response_model=schemas.Storefront)
async def create_storefront(
    *,
    db: AsyncSession = Depends(get_db),
    storefront_in: schemas.StorefrontCreate,
    current_user: User = Depends(PermissionChecker("manage_company")),
    _plan: User = Depends(PlanLimitChecker(resource="storefronts", count_model=Storefront)),
) -> Any:
    # A company owns one public storefront.  Keeping the rule in the write
    # path lets existing tenants with historic duplicate rows keep working
    # while preventing any new split-store configuration.
    # Lock the company row first so two concurrent create requests cannot both
    # observe an empty storefront list and create duplicates.
    await db.execute(
        select(Company.id)
        .where(Company.id == current_user.company_id)
        .with_for_update()
    )
    existing_storefront = await db.scalar(
        select(Storefront.id).where(
            Storefront.company_id == current_user.company_id,
            Storefront.is_active == True,
        ).limit(1)
    )
    if existing_storefront:
        raise HTTPException(
            status_code=409,
            detail="La empresa ya tiene una tienda. Actualiza la tienda existente.",
        )

    if not storefront_in.name or not storefront_in.name.strip():
        raise HTTPException(status_code=422, detail="El nombre de la tienda es obligatorio.")

    await _validate_storefront_price_list(db, storefront_in.price_list_id, current_user.company_id)

    slug = await _available_storefront_slug(db, current_user.company_id, storefront_in.name)
    subdomain = await _available_storefront_subdomain(db, storefront_in.name)
    storefront_data = storefront_in.model_dump(exclude={"slug", "subdomain"})
    storefront = Storefront(
        **storefront_data,
        slug=slug,
        subdomain=subdomain,
        company_id=current_user.company_id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(storefront)
    try:
        await db.flush()
        initial_theme = build_home_document(storefront.theme_settings)
        db.add(StorefrontThemeDocumentModel(
            storefront_id=storefront.id,
            company_id=current_user.company_id,
            template_key="home",
            draft_document=initial_theme,
            published_document=initial_theme,
            draft_version=1,
            published_version=1,
            published_at=datetime.now(timezone.utc),
            published_by_id=current_user.id,
            created_by_id=current_user.id,
            updated_by_id=current_user.id,
        ))
        await ensure_default_shipping_configuration(db, storefront, current_user.id)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No se pudo reservar la URL automática. Intenta guardar de nuevo.",
        ) from exc
    await db.refresh(storefront)
    return storefront


@router.put("/{storefront_id}", response_model=schemas.Storefront)
async def update_storefront(
    *,
    db: AsyncSession = Depends(get_db),
    storefront_id: uuid.UUID,
    storefront_in: schemas.StorefrontUpdate,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    storefront = await _get_storefront_or_404(db, storefront_id, current_user.company_id)
    # Repair legacy rows created before automatic URLs were introduced without
    # changing URLs that are already in use.
    if not storefront.slug:
        storefront.slug = await _available_storefront_slug(db, current_user.company_id, storefront.name)
    if not storefront.subdomain:
        storefront.subdomain = await _available_storefront_subdomain(db, storefront.name)
    update_payload = storefront_in.model_dump(exclude_unset=True)
    if "price_list_id" in update_payload:
        await _validate_storefront_price_list(db, storefront_in.price_list_id, current_user.company_id)
    for field, value in update_payload.items():
        setattr(storefront, field, value)
    storefront.updated_by_id = current_user.id
    db.add(storefront)
    # Keep the old form/API compatible during rollout. A legacy home update was
    # historically published immediately, so mirror it into both theme states
    # while preserving the new section order and visibility settings.
    legacy_theme_settings = update_payload.get("theme_settings")
    if isinstance(legacy_theme_settings, dict) and isinstance(legacy_theme_settings.get("home"), dict):
        theme_document = await _get_theme_document(
            db,
            storefront,
            "home",
            create=True,
            user_id=current_user.id,
            lock=True,
        )
        current_document = theme_document.published_document if isinstance(theme_document.published_document, dict) else {}
        compatible_document = {
            **current_document,
            "template": "home",
            "legacy_home": legacy_theme_settings["home"],
        }
        try:
            normalized_theme = normalize_home_document(compatible_document, storefront.theme_settings)
            await _validate_theme_references(db, storefront, normalized_theme)
        except ValueError as exc:
            await db.rollback()
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        next_published_version = theme_document.published_version + 1
        theme_document.draft_document = normalized_theme
        theme_document.published_document = normalized_theme
        theme_document.draft_version += 1
        theme_document.published_version = next_published_version
        theme_document.published_at = datetime.now(timezone.utc)
        theme_document.published_by_id = current_user.id
        theme_document.updated_by_id = current_user.id
        db.add(theme_document)
        db.add(StorefrontThemeRevisionModel(
            theme_document_id=theme_document.id,
            storefront_id=storefront.id,
            company_id=current_user.company_id,
            template_key="home",
            version=next_published_version,
            document=normalized_theme,
            operation="publish",
            created_by_id=current_user.id,
            updated_by_id=current_user.id,
        ))
        await log_activity(
            db,
            action="THEME_LEGACY_HOME_SYNCED",
            entity_type="StorefrontThemeDocument",
            entity_id=str(theme_document.id),
            user_id=current_user.id,
            company_id=current_user.company_id,
            details={"storefront_id": str(storefront.id), "template_key": "home", "published_version": next_published_version},
        )
    await db.commit()
    await db.refresh(storefront)
    return storefront


@router.get("/{storefront_id}/theme/components")
async def read_theme_component_registry(
    storefront_id: uuid.UUID,
    template_key: str = "home",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> dict[str, Any]:
    """Return the safe component palette available to the current tenant."""
    await _get_storefront_or_404(db, storefront_id, current_user.company_id)
    template_key = _theme_template_or_422(template_key)
    return {"template_key": template_key, "components": component_registry(template_key)}


@router.get("/{storefront_id}/media", response_model=List[schemas.StorefrontMediaAsset])
async def read_storefront_media(
    storefront_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> list[schemas.StorefrontMediaAsset]:
    """List only images owned by the current company's storefront."""
    storefront = await _get_storefront_or_404(db, storefront_id, current_user.company_id)
    result = await db.execute(
        select(StorefrontMediaAsset).where(
            StorefrontMediaAsset.storefront_id == storefront.id,
            StorefrontMediaAsset.company_id == current_user.company_id,
            StorefrontMediaAsset.is_active == True,
        ).order_by(StorefrontMediaAsset.created_at.desc()).limit(MAX_STOREFRONT_MEDIA_ASSETS)
    )
    return [_serialize_storefront_media_asset(asset) for asset in result.scalars().all()]


@router.get("/{storefront_id}/media/{asset_id}")
async def read_storefront_media_asset(
    storefront_id: uuid.UUID,
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> FileResponse:
    """Serve one uploaded image through the authenticated tenant boundary."""
    storefront = await _get_storefront_or_404(db, storefront_id, current_user.company_id)
    asset = await db.scalar(
        select(StorefrontMediaAsset).where(
            StorefrontMediaAsset.id == asset_id,
            StorefrontMediaAsset.storefront_id == storefront.id,
            StorefrontMediaAsset.company_id == current_user.company_id,
            StorefrontMediaAsset.is_active == True,
        )
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Imagen no encontrada.")
    _, file_path = _resolve_public_asset_path(asset.storage_path)
    return FileResponse(
        file_path,
        media_type=asset.content_type,
        headers={"Cache-Control": "private, no-store"},
    )


@router.post("/{storefront_id}/media", response_model=schemas.StorefrontMediaAsset)
async def upload_storefront_media(
    storefront_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> schemas.StorefrontMediaAsset:
    """Upload a validated image and register it under one storefront tenant."""
    storefront = await _get_storefront_or_404(db, storefront_id, current_user.company_id)
    current_count = await db.scalar(
        select(func.count(StorefrontMediaAsset.id)).where(
            StorefrontMediaAsset.storefront_id == storefront.id,
            StorefrontMediaAsset.company_id == current_user.company_id,
            StorefrontMediaAsset.is_active == True,
        )
    )
    if int(current_count or 0) >= MAX_STOREFRONT_MEDIA_ASSETS:
        raise HTTPException(
            status_code=409,
            detail=f"Esta tienda alcanzó el límite de {MAX_STOREFRONT_MEDIA_ASSETS} imágenes.",
        )

    stored = await save_image_upload(file)
    asset = StorefrontMediaAsset(
        storefront_id=storefront.id,
        company_id=current_user.company_id,
        storage_path=str(stored["storage_path"]),
        original_filename=_safe_media_filename(
            str(stored.get("file_name") or ""),
            str(stored["storage_path"]).rsplit("/", 1)[-1],
        ),
        content_type=str(stored["content_type"]),
        size_bytes=int(stored["size_bytes"]),
        width=int(stored["width"]),
        height=int(stored["height"]),
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(asset)
    try:
        await log_activity(
            db,
            action="STOREFRONT_MEDIA_UPLOADED",
            entity_type="StorefrontMediaAsset",
            entity_id=str(asset.id),
            user_id=current_user.id,
            company_id=current_user.company_id,
            details={
                "storefront_id": str(storefront.id),
                "content_type": asset.content_type,
                "size_bytes": asset.size_bytes,
            },
        )
        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.exception(
            "Failed to register storefront media asset",
            extra={
                "storefront_id": str(storefront.id),
                "company_id": str(current_user.company_id),
            },
        )
        try:
            Path(str(stored["file_path"])).unlink(missing_ok=True)
        except OSError:
            pass
        raise HTTPException(status_code=500, detail="No fue posible registrar la imagen.") from exc
    await db.refresh(asset)
    return _serialize_storefront_media_asset(asset)


@router.post(
    "/{storefront_id}/theme/{template_key}/preview-session",
    response_model=schemas.StorefrontThemePreviewSession,
)
async def create_theme_preview_session(
    storefront_id: uuid.UUID,
    template_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> schemas.StorefrontThemePreviewSession:
    template_key = _theme_template_or_422(template_key)
    storefront = await _get_storefront_or_404(db, storefront_id, current_user.company_id)
    preview_url = _storefront_preview_url(storefront)
    if not preview_url:
        raise HTTPException(
            status_code=422,
            detail="La tienda no tiene un subdominio de plataforma válido para previsualizar.",
        )
    token, expires_at = _create_storefront_theme_preview_session(storefront, current_user.id, template_key)
    return schemas.StorefrontThemePreviewSession(
        token=token,
        expires_at=expires_at,
        preview_url=f"{preview_url}?lumefy_preview=1&preview_token={quote(token, safe='')}",
        template_key=template_key,
    )


@router.get("/{storefront_id}/theme/{template_key}", response_model=schemas.StorefrontThemeDocument)
async def read_theme_document(
    storefront_id: uuid.UUID,
    template_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> schemas.StorefrontThemeDocument:
    template_key = _theme_template_or_422(template_key)
    storefront = await _get_storefront_or_404(db, storefront_id, current_user.company_id)
    document = await _get_theme_document(
        db,
        storefront,
        template_key,
        create=True,
        user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(document)
    return _serialize_theme_document(document, storefront.theme_settings, storefront)


@router.put("/{storefront_id}/theme/{template_key}/draft", response_model=schemas.StorefrontThemeDocument)
async def save_theme_draft(
    storefront_id: uuid.UUID,
    template_key: str,
    draft_in: schemas.StorefrontThemeDraftUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> schemas.StorefrontThemeDocument:
    template_key = _theme_template_or_422(template_key)
    storefront = await _get_storefront_or_404(db, storefront_id, current_user.company_id)
    document = await _get_theme_document(
        db,
        storefront,
        template_key,
        create=True,
        user_id=current_user.id,
        lock=True,
    )
    if draft_in.expected_draft_version != document.draft_version:
        raise HTTPException(
            status_code=409,
            detail="El borrador cambió mientras lo editabas. Recarga la tienda antes de guardar.",
        )
    try:
        normalized = _normalize_theme_document(template_key, draft_in.document, storefront.theme_settings)
        await _validate_theme_references(db, storefront, normalized)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    document.draft_document = normalized
    document.draft_version += 1
    document.updated_by_id = current_user.id
    db.add(document)
    await log_activity(
        db,
        action="THEME_DRAFT_SAVED",
        entity_type="StorefrontThemeDocument",
        entity_id=str(document.id),
        user_id=current_user.id,
        company_id=current_user.company_id,
        details={"storefront_id": str(storefront.id), "template_key": template_key, "draft_version": document.draft_version},
    )
    await db.commit()
    await db.refresh(document)
    return _serialize_theme_document(document, storefront.theme_settings, storefront)


@router.post("/{storefront_id}/theme/{template_key}/publish", response_model=schemas.StorefrontThemeDocument)
async def publish_theme_document(
    storefront_id: uuid.UUID,
    template_key: str,
    publish_in: schemas.StorefrontThemePublishRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> schemas.StorefrontThemeDocument:
    template_key = _theme_template_or_422(template_key)
    storefront = await _get_storefront_or_404(db, storefront_id, current_user.company_id)
    document = await _get_theme_document(
        db,
        storefront,
        template_key,
        create=True,
        user_id=current_user.id,
        lock=True,
    )
    expected_version = publish_in.expected_draft_version if publish_in else None
    if expected_version is not None and expected_version != document.draft_version:
        raise HTTPException(
            status_code=409,
            detail="El borrador cambió mientras lo editabas. Recarga la tienda antes de publicar.",
        )
    try:
        published = _normalize_theme_document(template_key, document.draft_document, storefront.theme_settings)
        await _validate_theme_references(db, storefront, published)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    next_version = document.published_version + 1
    document.published_document = published
    document.published_version = next_version
    document.published_at = datetime.now(timezone.utc)
    document.published_by_id = current_user.id
    document.updated_by_id = current_user.id
    db.add(document)
    db.add(StorefrontThemeRevisionModel(
        theme_document_id=document.id,
        storefront_id=storefront.id,
        company_id=current_user.company_id,
        template_key=template_key,
        version=next_version,
        document=published,
        operation="publish",
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    ))
    await log_activity(
        db,
        action="THEME_PUBLISHED",
        entity_type="StorefrontThemeDocument",
        entity_id=str(document.id),
        user_id=current_user.id,
        company_id=current_user.company_id,
        details={"storefront_id": str(storefront.id), "template_key": template_key, "published_version": next_version},
    )
    await db.commit()
    await db.refresh(document)
    return _serialize_theme_document(document, storefront.theme_settings, storefront)


@router.get("/{storefront_id}/theme/{template_key}/revisions", response_model=List[schemas.StorefrontThemeRevision])
async def read_theme_revisions(
    storefront_id: uuid.UUID,
    template_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> list[schemas.StorefrontThemeRevision]:
    template_key = _theme_template_or_422(template_key)
    storefront = await _get_storefront_or_404(db, storefront_id, current_user.company_id)
    result = await db.execute(
        select(StorefrontThemeRevisionModel).where(
            StorefrontThemeRevisionModel.storefront_id == storefront.id,
            StorefrontThemeRevisionModel.company_id == current_user.company_id,
            StorefrontThemeRevisionModel.template_key == template_key,
            StorefrontThemeRevisionModel.is_active == True,
        ).order_by(StorefrontThemeRevisionModel.version.desc()).limit(50)
    )
    return [
        schemas.StorefrontThemeRevision.model_validate(item, from_attributes=True)
        for item in result.scalars().all()
    ]


@router.post("/{storefront_id}/theme/{template_key}/restore/{revision_id}", response_model=schemas.StorefrontThemeDocument)
async def restore_theme_revision(
    storefront_id: uuid.UUID,
    template_key: str,
    revision_id: uuid.UUID,
    restore_in: schemas.StorefrontThemeRestoreRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> schemas.StorefrontThemeDocument:
    template_key = _theme_template_or_422(template_key)
    storefront = await _get_storefront_or_404(db, storefront_id, current_user.company_id)
    document = await _get_theme_document(
        db,
        storefront,
        template_key,
        create=True,
        user_id=current_user.id,
        lock=True,
    )
    expected_version = restore_in.expected_draft_version if restore_in else None
    if expected_version is not None and expected_version != document.draft_version:
        raise HTTPException(
            status_code=409,
            detail="El borrador cambió mientras lo editabas. Recarga la tienda antes de restaurar.",
        )
    revision = await db.scalar(
        select(StorefrontThemeRevisionModel).where(
            StorefrontThemeRevisionModel.id == revision_id,
            StorefrontThemeRevisionModel.theme_document_id == document.id,
            StorefrontThemeRevisionModel.storefront_id == storefront.id,
            StorefrontThemeRevisionModel.company_id == current_user.company_id,
            StorefrontThemeRevisionModel.template_key == template_key,
            StorefrontThemeRevisionModel.is_active == True,
        )
    )
    if not revision:
        raise HTTPException(status_code=404, detail="La revisión no existe en esta tienda")
    try:
        restored = _normalize_theme_document(template_key, revision.document, storefront.theme_settings)
        await _validate_theme_references(db, storefront, restored)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    document.draft_document = restored
    document.draft_version += 1
    document.updated_by_id = current_user.id
    db.add(document)
    await log_activity(
        db,
        action="THEME_REVISION_RESTORED",
        entity_type="StorefrontThemeDocument",
        entity_id=str(document.id),
        user_id=current_user.id,
        company_id=current_user.company_id,
        details={
            "storefront_id": str(storefront.id),
            "template_key": template_key,
            "revision_id": str(revision.id),
            "draft_version": document.draft_version,
        },
    )
    await db.commit()
    await db.refresh(document)
    return _serialize_theme_document(document, storefront.theme_settings, storefront)


@router.get("/{storefront_id}/readiness")
async def read_storefront_readiness(
    storefront_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    """Return the operational prerequisites that must be met before selling online."""
    storefront = await _get_storefront_or_404(db, storefront_id, current_user.company_id)
    products_result = await db.execute(
        select(PublishedProduct)
        .options(selectinload(PublishedProduct.product))
        .where(
            PublishedProduct.storefront_id == storefront.id,
            PublishedProduct.is_active == True,
            PublishedProduct.is_published == True,
        )
    )
    published_products = products_result.scalars().all()
    stock_map = await _get_storefront_stock_map(
        db,
        storefront,
        [item.product_id for item in published_products],
    )
    out_of_stock_count = sum(
        1
        for item in published_products
        if item.product and item.product.track_inventory and sum(
            value for (product_id, _variant_id), value in stock_map.items() if product_id == item.product_id
        ) <= 0
    )
    gateways_result = await db.execute(
        select(StorePaymentGateway.id).where(
            StorePaymentGateway.storefront_id == storefront.id,
            StorePaymentGateway.is_active == True,
            StorePaymentGateway.is_enabled == True,
            StorePaymentGateway.provider.in_(SUPPORTED_PUBLIC_PAYMENT_PROVIDERS),
        )
    )
    enabled_gateways = len(gateways_result.scalars().all())
    issues: list[str] = []
    if not storefront.is_enabled:
        issues.append("La tienda está en borrador.")
    if not published_products:
        issues.append("Publica al menos un producto.")
    if out_of_stock_count:
        issues.append(f"{out_of_stock_count} producto(s) publicado(s) no tienen stock.")
    if not enabled_gateways:
        issues.append("Activa al menos una forma de pago.")

    try:
        await _resolve_storefront_fulfillment_warehouse(db, storefront)
    except HTTPException as exc:
        issues.append(str(exc.detail))

    return {
        "ready": not issues,
        "published_products": len(published_products),
        "out_of_stock_products": out_of_stock_count,
        "enabled_payment_gateways": enabled_gateways,
        "issues": issues,
    }


@router.get("/domains", response_model=List[schemas.StorefrontDomain])
async def read_storefront_domains(
    db: AsyncSession = Depends(get_db),
    storefront_id: uuid.UUID | None = None,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    query = select(StorefrontDomain).where(
        StorefrontDomain.company_id == current_user.company_id,
        StorefrontDomain.is_active == True,
    )
    if storefront_id:
        query = query.where(StorefrontDomain.storefront_id == storefront_id)
    result = await db.execute(query)
    domains = result.scalars().all()
    verification_token_created = False
    for domain in domains:
        # `any()` cannot consume asynchronous calls.  Every legacy domain must
        # also receive a token, not just the first one that needs it.
        if await _ensure_domain_verification_token(domain):
            verification_token_created = True
    if verification_token_created:
        await db.commit()
    return [_serialize_domain(domain) for domain in domains]


@router.post("/domains", response_model=schemas.StorefrontDomain)
async def create_storefront_domain(
    *,
    db: AsyncSession = Depends(get_db),
    domain_in: schemas.StorefrontDomainCreate,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    await _get_storefront_or_404(db, domain_in.storefront_id, current_user.company_id)
    normalized_domain = _normalize_custom_domain(domain_in.domain)
    platform_domain, _ = _platform_storefront_host_and_port()
    if platform_domain and (normalized_domain == platform_domain or normalized_domain.endswith(f".{platform_domain}")):
        raise HTTPException(status_code=422, detail="Ese dominio pertenece a la plataforma. Usa el subdominio de la tienda.")
    if domain_in.is_primary:
        await db.execute(
            select(StorefrontDomain).where(
                StorefrontDomain.storefront_id == domain_in.storefront_id,
                StorefrontDomain.company_id == current_user.company_id,
                StorefrontDomain.is_active == True,
            ).with_for_update()
        )
        await db.execute(
            StorefrontDomain.__table__.update()
            .where(StorefrontDomain.storefront_id == domain_in.storefront_id, StorefrontDomain.is_active == True)
            .values(is_primary=False)
        )
    domain = StorefrontDomain(
        domain=normalized_domain,
        storefront_id=domain_in.storefront_id,
        is_primary=domain_in.is_primary,
        is_verified=False,
        verification_token=secrets.token_urlsafe(24),
        company_id=current_user.company_id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(domain)
    await db.commit()
    await db.refresh(domain)
    return _serialize_domain(domain)


@router.put("/domains/{domain_id}", response_model=schemas.StorefrontDomain)
async def update_storefront_domain(
    *,
    db: AsyncSession = Depends(get_db),
    domain_id: uuid.UUID,
    domain_in: schemas.StorefrontDomainUpdate,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    result = await db.execute(
        select(StorefrontDomain).where(
            StorefrontDomain.id == domain_id,
            StorefrontDomain.company_id == current_user.company_id,
            StorefrontDomain.is_active == True,
        )
    )
    domain = result.scalars().first()
    if not domain:
        raise HTTPException(status_code=404, detail="Storefront domain not found")
    if domain_in.is_primary:
        await db.execute(
            StorefrontDomain.__table__.update()
            .where(
                StorefrontDomain.storefront_id == domain.storefront_id,
                StorefrontDomain.id != domain.id,
                StorefrontDomain.is_active == True,
            )
            .values(is_primary=False)
        )
    for field, value in domain_in.model_dump(exclude_unset=True).items():
        setattr(domain, field, value)
    domain.updated_by_id = current_user.id
    db.add(domain)
    await db.commit()
    await db.refresh(domain)
    return _serialize_domain(domain)


@router.post("/domains/{domain_id}/verify", response_model=schemas.StorefrontDomain)
async def verify_storefront_domain(
    *,
    db: AsyncSession = Depends(get_db),
    domain_id: uuid.UUID,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    domain = await db.scalar(
        select(StorefrontDomain).where(
            StorefrontDomain.id == domain_id,
            StorefrontDomain.company_id == current_user.company_id,
            StorefrontDomain.is_active == True,
        )
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Storefront domain not found")
    await _ensure_domain_verification_token(domain)
    if not await _verify_domain_txt_record(domain):
        db.add(domain)
        await db.commit()
        raise HTTPException(
            status_code=409,
            detail=f"No encontramos el TXT {_domain_verification_record(domain.domain)}. Publícalo y espera la propagación DNS.",
        )
    domain.is_verified = True
    domain.verified_at = datetime.now(timezone.utc)
    domain.updated_by_id = current_user.id
    db.add(domain)
    await db.commit()
    await db.refresh(domain)
    return _serialize_domain(domain)


@router.delete("/domains/{domain_id}")
async def delete_storefront_domain(
    *,
    db: AsyncSession = Depends(get_db),
    domain_id: uuid.UUID,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    result = await db.execute(
        select(StorefrontDomain).where(
            StorefrontDomain.id == domain_id,
            StorefrontDomain.company_id == current_user.company_id,
            StorefrontDomain.is_active == True,
        )
    )
    domain = result.scalars().first()
    if not domain:
        raise HTTPException(status_code=404, detail="Storefront domain not found")
    domain.is_active = False
    domain.updated_by_id = current_user.id
    db.add(domain)
    await db.commit()
    return {"ok": True}


@router.get("/collections", response_model=List[schemas.StoreCollection])
async def read_collections(
    db: AsyncSession = Depends(get_db),
    storefront_id: uuid.UUID | None = None,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    query = select(StoreCollection).where(
        StoreCollection.company_id == current_user.company_id,
        StoreCollection.is_active == True,
    )
    if storefront_id:
        query = query.where(StoreCollection.storefront_id == storefront_id)
    query = query.order_by(StoreCollection.sort_order.asc(), StoreCollection.name.asc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/collections", response_model=schemas.StoreCollection)
async def create_collection(
    *,
    db: AsyncSession = Depends(get_db),
    collection_in: schemas.StoreCollectionCreate,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    await _get_storefront_or_404(db, collection_in.storefront_id, current_user.company_id)
    collection = StoreCollection(
        **collection_in.model_dump(),
        company_id=current_user.company_id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(collection)
    await db.commit()
    await db.refresh(collection)
    return collection


@router.put("/collections/{collection_id}", response_model=schemas.StoreCollection)
async def update_collection(
    *,
    db: AsyncSession = Depends(get_db),
    collection_id: uuid.UUID,
    collection_in: schemas.StoreCollectionUpdate,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    collection = await _get_collection_or_404(db, collection_id, current_user.company_id)
    for field, value in collection_in.model_dump(exclude_unset=True).items():
        setattr(collection, field, value)
    collection.updated_by_id = current_user.id
    db.add(collection)
    await db.commit()
    await db.refresh(collection)
    return collection


@router.post("/collections/{collection_id}/products", response_model=schemas.StoreCollectionProduct)
async def add_product_to_collection(
    *,
    db: AsyncSession = Depends(get_db),
    collection_id: uuid.UUID,
    link_in: schemas.StoreCollectionProductCreate,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    collection = await _get_collection_or_404(db, collection_id, current_user.company_id)
    published_product = await _get_published_product_or_404(db, link_in.published_product_id, current_user.company_id)
    if published_product.storefront_id != collection.storefront_id:
        raise HTTPException(status_code=400, detail="Collection and published product must belong to the same storefront")

    result = await db.execute(
        select(StoreCollectionProduct).where(
            StoreCollectionProduct.collection_id == collection_id,
            StoreCollectionProduct.published_product_id == link_in.published_product_id,
        )
    )
    existing_link = result.scalars().first()
    if existing_link:
        existing_link.is_active = True
        existing_link.sort_order = link_in.sort_order
        existing_link.updated_by_id = current_user.id
        db.add(existing_link)
        await db.commit()
        await db.refresh(existing_link)
        return existing_link

    link = StoreCollectionProduct(
        collection_id=collection_id,
        published_product_id=link_in.published_product_id,
        sort_order=link_in.sort_order,
        company_id=current_user.company_id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


@router.get("/collections/{collection_id}/products", response_model=List[schemas.StoreCollectionProduct])
async def read_collection_products(
    collection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    await _get_collection_or_404(db, collection_id, current_user.company_id)
    result = await db.execute(
        select(StoreCollectionProduct).where(
            StoreCollectionProduct.collection_id == collection_id,
            StoreCollectionProduct.company_id == current_user.company_id,
            StoreCollectionProduct.is_active == True,
        ).order_by(StoreCollectionProduct.sort_order.asc(), StoreCollectionProduct.created_at.asc())
    )
    return result.scalars().all()


@router.delete("/collections/{collection_id}/products/{published_product_id}")
async def remove_product_from_collection(
    collection_id: uuid.UUID,
    published_product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    await _get_collection_or_404(db, collection_id, current_user.company_id)
    result = await db.execute(
        select(StoreCollectionProduct).where(
            StoreCollectionProduct.collection_id == collection_id,
            StoreCollectionProduct.published_product_id == published_product_id,
            StoreCollectionProduct.company_id == current_user.company_id,
            StoreCollectionProduct.is_active == True,
        )
    )
    link = result.scalars().first()
    if not link:
        raise HTTPException(status_code=404, detail="Collection product link not found")
    link.is_active = False
    link.updated_by_id = current_user.id
    db.add(link)
    await db.commit()
    return {"ok": True}


@router.get("/published-products", response_model=List[schemas.PublishedProduct])
async def read_published_products(
    db: AsyncSession = Depends(get_db),
    storefront_id: uuid.UUID | None = None,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    query = (
        select(PublishedProduct)
        .options(selectinload(PublishedProduct.product))
        .where(
        PublishedProduct.company_id == current_user.company_id,
        PublishedProduct.is_active == True,
        )
    )
    if storefront_id:
        query = query.where(PublishedProduct.storefront_id == storefront_id)
    query = query.order_by(PublishedProduct.sort_order.asc(), PublishedProduct.created_at.desc())
    result = await db.execute(query)
    return [_serialize_admin_published_product(item) for item in result.scalars().all()]


@router.post("/published-products", response_model=schemas.PublishedProduct)
async def create_published_product(
    *,
    db: AsyncSession = Depends(get_db),
    published_product_in: schemas.PublishedProductCreate,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    await _get_storefront_or_404(db, published_product_in.storefront_id, current_user.company_id)
    product_result = await db.execute(
        select(Product).where(
            Product.id == published_product_in.product_id,
            Product.company_id == current_user.company_id,
            Product.is_active == True,
        )
    )
    product = product_result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    published_product = PublishedProduct(
        **published_product_in.model_dump(),
        company_id=current_user.company_id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(published_product)
    await db.commit()
    await db.refresh(published_product, attribute_names=["product"])
    return _serialize_admin_published_product(published_product)


@router.put("/published-products/{published_product_id}", response_model=schemas.PublishedProduct)
async def update_published_product(
    *,
    db: AsyncSession = Depends(get_db),
    published_product_id: uuid.UUID,
    published_product_in: schemas.PublishedProductUpdate,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    published_product = await _get_published_product_or_404(db, published_product_id, current_user.company_id)
    for field, value in published_product_in.model_dump(exclude_unset=True).items():
        setattr(published_product, field, value)
    published_product.updated_by_id = current_user.id
    db.add(published_product)
    await db.commit()
    await db.refresh(published_product, attribute_names=["product"])
    return _serialize_admin_published_product(published_product)


@router.get("/navigation", response_model=List[schemas.StoreNavigationItem])
async def read_navigation(
    db: AsyncSession = Depends(get_db),
    storefront_id: uuid.UUID | None = None,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    query = select(StoreNavigationItem).where(
        StoreNavigationItem.company_id == current_user.company_id,
        StoreNavigationItem.is_active == True,
    )
    if storefront_id:
        query = query.where(StoreNavigationItem.storefront_id == storefront_id)
    query = query.order_by(StoreNavigationItem.sort_order.asc(), StoreNavigationItem.created_at.asc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/navigation", response_model=schemas.StoreNavigationItem)
async def create_navigation_item(
    *,
    db: AsyncSession = Depends(get_db),
    item_in: schemas.StoreNavigationItemCreate,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    await _get_storefront_or_404(db, item_in.storefront_id, current_user.company_id)
    if item_in.parent_id:
        await _get_navigation_item_or_404(db, item_in.parent_id, current_user.company_id)
    item = StoreNavigationItem(
        **item_in.model_dump(),
        company_id=current_user.company_id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.put("/navigation/{navigation_item_id}", response_model=schemas.StoreNavigationItem)
async def update_navigation_item(
    *,
    db: AsyncSession = Depends(get_db),
    navigation_item_id: uuid.UUID,
    item_in: schemas.StoreNavigationItemUpdate,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    item = await _get_navigation_item_or_404(db, navigation_item_id, current_user.company_id)
    for field, value in item_in.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    item.updated_by_id = current_user.id
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/navigation/{navigation_item_id}", response_model=dict)
async def delete_navigation_item(
    *,
    db: AsyncSession = Depends(get_db),
    navigation_item_id: uuid.UUID,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    item = await _get_navigation_item_or_404(db, navigation_item_id, current_user.company_id)
    await _deactivate_navigation_branch(db, item, current_user.id)
    await db.commit()
    return {"ok": True}


@router.get("/payment-gateways", response_model=List[schemas.StorePaymentGateway])
async def read_payment_gateways(
    db: AsyncSession = Depends(get_db),
    storefront_id: uuid.UUID | None = None,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    query = select(StorePaymentGateway).where(
        StorePaymentGateway.company_id == current_user.company_id,
        StorePaymentGateway.is_active == True,
    )
    if storefront_id:
        query = query.where(StorePaymentGateway.storefront_id == storefront_id)
    query = query.order_by(StorePaymentGateway.sort_order.asc(), StorePaymentGateway.display_name.asc())
    result = await db.execute(query)
    return [_serialize_admin_payment_gateway(gateway) for gateway in result.scalars().all()]


@router.post("/payment-gateways", response_model=schemas.StorePaymentGateway)
async def create_payment_gateway(
    *,
    db: AsyncSession = Depends(get_db),
    gateway_in: schemas.StorePaymentGatewayCreate,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    await _get_storefront_or_404(db, gateway_in.storefront_id, current_user.company_id)
    payload = gateway_in.model_dump()
    payload["provider"] = _validate_payment_gateway_provider(gateway_in.provider)
    gateway = StorePaymentGateway(
        **payload,
        company_id=current_user.company_id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(gateway)
    await db.commit()
    await db.refresh(gateway)
    return _serialize_admin_payment_gateway(gateway)


async def _get_shipping_destination_or_404(
    db: AsyncSession,
    destination_id: uuid.UUID,
    company_id: uuid.UUID,
) -> StorefrontShippingDestination:
    destination = await db.scalar(
        select(StorefrontShippingDestination).where(
            StorefrontShippingDestination.id == destination_id,
            StorefrontShippingDestination.company_id == company_id,
            StorefrontShippingDestination.is_active == True,
        )
    )
    if not destination:
        raise HTTPException(status_code=404, detail="Destino de envío no encontrado")
    return destination


async def _get_shipping_method_or_404(
    db: AsyncSession,
    method_id: uuid.UUID,
    company_id: uuid.UUID,
) -> StorefrontShippingMethod:
    method = await db.scalar(
        select(StorefrontShippingMethod).where(
            StorefrontShippingMethod.id == method_id,
            StorefrontShippingMethod.company_id == company_id,
            StorefrontShippingMethod.is_active == True,
        )
    )
    if not method:
        raise HTTPException(status_code=404, detail="Método de envío no encontrado")
    return method


async def _get_shipping_rule_or_404(
    db: AsyncSession,
    rule_id: uuid.UUID,
    company_id: uuid.UUID,
) -> StorefrontShippingRule:
    rule = await db.scalar(
        select(StorefrontShippingRule).where(
            StorefrontShippingRule.id == rule_id,
            StorefrontShippingRule.company_id == company_id,
            StorefrontShippingRule.is_active == True,
        )
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Regla de envío no encontrada")
    return rule


def _validate_shipping_method_payload(payload: dict) -> None:
    method_type = str(payload.get("method_type") or "delivery").lower()
    if method_type not in {"delivery", "pickup", "quote"}:
        raise HTTPException(status_code=422, detail="El tipo de método de envío no es válido")
    if payload.get("estimate_min_days") is not None and payload.get("estimate_max_days") is not None:
        if payload["estimate_min_days"] > payload["estimate_max_days"]:
            raise HTTPException(status_code=422, detail="El tiempo mínimo no puede superar al máximo")


@router.get("/shipping/config")
async def read_shipping_config(
    db: AsyncSession = Depends(get_db),
    storefront_id: uuid.UUID | None = None,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    if not storefront_id:
        raise HTTPException(status_code=422, detail="Selecciona una tienda")
    storefront = await _get_storefront_or_404(db, storefront_id, current_user.company_id)
    created = await ensure_default_shipping_configuration(db, storefront, current_user.id)
    destinations_result = await db.execute(
        select(StorefrontShippingDestination).where(
            StorefrontShippingDestination.storefront_id == storefront.id,
            StorefrontShippingDestination.is_active == True,
        ).order_by(StorefrontShippingDestination.sort_order.asc(), StorefrontShippingDestination.state_name.asc(), StorefrontShippingDestination.city_name.asc())
    )
    methods_result = await db.execute(
        select(StorefrontShippingMethod).where(
            StorefrontShippingMethod.storefront_id == storefront.id,
            StorefrontShippingMethod.is_active == True,
        ).order_by(StorefrontShippingMethod.sort_order.asc(), StorefrontShippingMethod.name.asc())
    )
    rules_result = await db.execute(
        select(StorefrontShippingRule).where(
            StorefrontShippingRule.storefront_id == storefront.id,
            StorefrontShippingRule.is_active == True,
        ).order_by(StorefrontShippingRule.priority.asc(), StorefrontShippingRule.created_at.asc())
    )
    if created:
        await db.commit()
    return {
        "destinations": [schemas.StorefrontShippingDestination.model_validate(item) for item in destinations_result.scalars().all()],
        "methods": [schemas.StorefrontShippingMethod.model_validate(item) for item in methods_result.scalars().all()],
        "rules": [schemas.StorefrontShippingRule.model_validate(item) for item in rules_result.scalars().all()],
    }


@router.post("/shipping/destinations", response_model=schemas.StorefrontShippingDestination)
async def create_shipping_destination(
    destination_in: schemas.StorefrontShippingDestinationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    await _get_storefront_or_404(db, destination_in.storefront_id, current_user.company_id)
    payload = destination_in.model_dump()
    payload["country_code"] = (payload.get("country_code") or "CO").strip().upper()
    payload["destination_type"] = (payload.get("destination_type") or "city").lower()
    if payload["destination_type"] not in {"department", "city"}:
        raise HTTPException(status_code=422, detail="El tipo de destino debe ser departamento o ciudad")
    if payload["destination_type"] == "department":
        payload["city_code"] = None
        payload["city_name"] = None
    elif not payload.get("city_name") and not payload.get("city_code"):
        raise HTTPException(status_code=422, detail="Una ciudad requiere nombre o código")
    destination = StorefrontShippingDestination(
        **payload,
        company_id=current_user.company_id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(destination)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ese destino ya existe en la tienda") from exc
    await db.refresh(destination)
    return destination


def _normalize_import_column(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _import_cell_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        import pandas as pd
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _import_cell_code(value: Any) -> str:
    text = _import_cell_text(value)
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text


def _shipping_destination_name_key(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text).strip().casefold()


@router.post("/shipping/destinations/import", response_model=dict)
async def import_shipping_destinations(
    storefront_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    """Import shipping departments/cities from an Excel or CSV file."""
    await _get_storefront_or_404(db, storefront_id, current_user.company_id)

    filename = (file.filename or "").lower()
    if not filename.endswith((".csv", ".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="Formato inválido. Usa un archivo .xlsx, .xls o .csv.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="El archivo no puede superar 10 MB.")

    import io
    import pandas as pd

    try:
        source = io.BytesIO(content)
        if filename.endswith(".csv"):
            dataframe = pd.read_csv(source, dtype=object)
        else:
            dataframe = pd.read_excel(source, dtype=object)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"No se pudo leer el archivo: {exc}") from exc

    if dataframe.empty:
        raise HTTPException(status_code=422, detail="El archivo no contiene filas para importar.")
    if len(dataframe.index) > 10000:
        raise HTTPException(status_code=422, detail="El archivo no puede contener más de 10.000 filas.")

    aliases = {
        "country_code": {"country_code", "codigo_pais", "pais", "country"},
        "state_code": {"state_code", "department_code", "departamento_codigo", "codigo_departamento", "depto_codigo", "codigo_depto"},
        "state_name": {"state_name", "department", "departamento", "department_name", "nombre_departamento", "depto", "depto_nombre"},
        "city_code": {"city_code", "municipality_code", "municipio_codigo", "codigo_municipio", "codigo_ciudad", "city_id"},
        "city_name": {"city_name", "city", "municipality", "municipio", "ciudad", "nombre_ciudad", "nombre_municipio"},
        "destination_type": {"destination_type", "tipo_destino", "tipo"},
        "sort_order": {"sort_order", "orden", "prioridad"},
    }
    normalized_columns = {_normalize_import_column(column): column for column in dataframe.columns}
    selected_columns: dict[str, Any] = {}
    for field, field_aliases in aliases.items():
        source_column = next((normalized_columns[alias] for alias in field_aliases if alias in normalized_columns), None)
        if source_column is not None:
            selected_columns[field] = source_column
    if "state_name" not in selected_columns:
        raise HTTPException(status_code=422, detail="Falta una columna de departamento. Usa state_name o departamento.")

    existing_result = await db.execute(
        select(StorefrontShippingDestination).where(
            StorefrontShippingDestination.storefront_id == storefront_id,
            StorefrontShippingDestination.company_id == current_user.company_id,
        )
    )
    existing_destinations = existing_result.scalars().all()
    existing_by_code: dict[tuple[str, str, str, str], StorefrontShippingDestination] = {}
    existing_by_name: dict[tuple[str, str, str, str], StorefrontShippingDestination] = {}

    def add_existing_index(destination: StorefrontShippingDestination) -> None:
        country = (destination.country_code or "CO").strip().upper()
        state_code = (destination.state_code or "").strip().casefold()
        city_code = (destination.city_code or "").strip().casefold()
        state_name = _shipping_destination_name_key(destination.state_name)
        city_name = _shipping_destination_name_key(destination.city_name)
        if state_code or city_code:
            existing_by_code[(country, state_code, city_code, destination.destination_type)] = destination
        existing_by_name[(country, state_name, city_name, destination.destination_type)] = destination

    for existing in existing_destinations:
        add_existing_index(existing)

    created_count = 0
    updated_count = 0
    skipped_count = 0
    errors: list[str] = []

    for index, row in dataframe.iterrows():
        row_number = int(index) + 2
        try:
            def cell(field: str) -> str:
                return _import_cell_text(row.get(selected_columns[field])) if field in selected_columns else ""

            state_name = cell("state_name")
            if not state_name:
                skipped_count += 1
                continue
            country_code = _import_cell_code(cell("country_code")) or "CO"
            country_code = country_code.upper()
            state_code = _import_cell_code(cell("state_code"))
            city_code = _import_cell_code(cell("city_code"))
            city_name = cell("city_name")
            destination_type = cell("destination_type").casefold()
            if destination_type in {"departamento", "department", "depto"}:
                destination_type = "department"
            elif destination_type in {"ciudad", "city", "municipio", "municipality"}:
                destination_type = "city"
            else:
                destination_type = "city" if city_name or city_code else "department"
            if destination_type == "department":
                city_code = ""
                city_name = ""
            elif not city_name and not city_code:
                raise ValueError("una ciudad requiere city_name/ciudad o city_code/codigo_ciudad")

            sort_order_text = cell("sort_order")
            sort_order = int(float(sort_order_text)) if sort_order_text else 0
            identity_code = (country_code, state_code.casefold(), city_code.casefold(), destination_type)
            identity_name = (
                country_code,
                _shipping_destination_name_key(state_name),
                _shipping_destination_name_key(city_name),
                destination_type,
            )
            destination = existing_by_code.get(identity_code) if (state_code or city_code) else None
            destination = destination or existing_by_name.get(identity_name)
            if destination:
                destination.country_code = country_code
                destination.state_code = state_code or None
                destination.state_name = state_name
                destination.city_code = city_code or None
                destination.city_name = city_name or None
                destination.destination_type = destination_type
                destination.sort_order = sort_order
                destination.is_active = True
                destination.updated_by_id = current_user.id
                updated_count += 1
            else:
                destination = StorefrontShippingDestination(
                    storefront_id=storefront_id,
                    company_id=current_user.company_id,
                    created_by_id=current_user.id,
                    updated_by_id=current_user.id,
                    country_code=country_code,
                    state_code=state_code or None,
                    state_name=state_name,
                    city_code=city_code or None,
                    city_name=city_name or None,
                    destination_type=destination_type,
                    sort_order=sort_order,
                )
                db.add(destination)
                created_count += 1
            add_existing_index(destination)
        except (TypeError, ValueError, OverflowError) as exc:
            errors.append(f"Fila {row_number}: {exc}")

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="El archivo contiene destinos duplicados o datos en conflicto.") from exc

    return {
        "success": True,
        "count": created_count + updated_count,
        "created": created_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "error_count": len(errors),
        "errors": errors[:100],
    }


@router.put("/shipping/destinations/{destination_id}", response_model=schemas.StorefrontShippingDestination)
async def update_shipping_destination(
    destination_id: uuid.UUID,
    destination_in: schemas.StorefrontShippingDestinationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    destination = await _get_shipping_destination_or_404(db, destination_id, current_user.company_id)
    for field, value in destination_in.model_dump(exclude_unset=True).items():
        setattr(destination, field, value)
    destination.country_code = (destination.country_code or "CO").strip().upper()
    destination.destination_type = (destination.destination_type or "city").lower()
    if destination.destination_type not in {"department", "city"}:
        raise HTTPException(status_code=422, detail="El tipo de destino debe ser departamento o ciudad")
    if destination.destination_type == "department":
        destination.city_code = None
        destination.city_name = None
    elif not destination.city_name and not destination.city_code:
        raise HTTPException(status_code=422, detail="Una ciudad requiere nombre o código")
    destination.updated_by_id = current_user.id
    db.add(destination)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ese destino ya existe en la tienda") from exc
    await db.refresh(destination)
    return destination


@router.delete("/shipping/destinations/{destination_id}", response_model=dict)
async def delete_shipping_destination(
    destination_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    destination = await _get_shipping_destination_or_404(db, destination_id, current_user.company_id)
    destination.is_active = False
    destination.updated_by_id = current_user.id
    db.add(destination)
    await db.commit()
    return {"ok": True}


@router.post("/shipping/methods", response_model=schemas.StorefrontShippingMethod)
async def create_shipping_method(
    method_in: schemas.StorefrontShippingMethodCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    await _get_storefront_or_404(db, method_in.storefront_id, current_user.company_id)
    payload = method_in.model_dump()
    payload["code"] = payload["code"].strip().lower().replace(" ", "-")
    _validate_shipping_method_payload(payload)
    method = StorefrontShippingMethod(
        **payload,
        company_id=current_user.company_id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(method)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ese código de método ya existe en la tienda") from exc
    await db.refresh(method)
    return method


@router.put("/shipping/methods/{method_id}", response_model=schemas.StorefrontShippingMethod)
async def update_shipping_method(
    method_id: uuid.UUID,
    method_in: schemas.StorefrontShippingMethodUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    method = await _get_shipping_method_or_404(db, method_id, current_user.company_id)
    for field, value in method_in.model_dump(exclude_unset=True).items():
        setattr(method, field, value)
    method.code = method.code.strip().lower().replace(" ", "-")
    _validate_shipping_method_payload({field: getattr(method, field) for field in ["method_type", "estimate_min_days", "estimate_max_days"]})
    method.updated_by_id = current_user.id
    db.add(method)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ese código de método ya existe en la tienda") from exc
    await db.refresh(method)
    return method


@router.delete("/shipping/methods/{method_id}", response_model=dict)
async def delete_shipping_method(
    method_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    method = await _get_shipping_method_or_404(db, method_id, current_user.company_id)
    method.is_active = False
    method.is_enabled = False
    method.updated_by_id = current_user.id
    db.add(method)
    await db.commit()
    return {"ok": True}


@router.post("/shipping/rules", response_model=schemas.StorefrontShippingRule)
async def create_shipping_rule(
    rule_in: schemas.StorefrontShippingRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    storefront = await _get_storefront_or_404(db, rule_in.storefront_id, current_user.company_id)
    method = await _get_shipping_method_or_404(db, rule_in.method_id, current_user.company_id)
    if method.storefront_id != storefront.id:
        raise HTTPException(status_code=422, detail="El método no pertenece a la tienda seleccionada")
    validate_shipping_rule_values(rule_in)
    payload = rule_in.model_dump()
    payload["destination_type"] = (payload.get("destination_type") or "global").lower()
    payload["charge_type"] = (payload.get("charge_type") or "flat").lower()
    payload["payment_provider"] = (payload.get("payment_provider") or "").strip().lower() or None
    rule = StorefrontShippingRule(
        **payload,
        company_id=current_user.company_id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.put("/shipping/rules/{rule_id}", response_model=schemas.StorefrontShippingRule)
async def update_shipping_rule(
    rule_id: uuid.UUID,
    rule_in: schemas.StorefrontShippingRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    rule = await _get_shipping_rule_or_404(db, rule_id, current_user.company_id)
    payload = rule_in.model_dump(exclude_unset=True)
    if "method_id" in payload:
        method = await _get_shipping_method_or_404(db, payload["method_id"], current_user.company_id)
        if method.storefront_id != rule.storefront_id:
            raise HTTPException(status_code=422, detail="El método no pertenece a la tienda seleccionada")
    for field, value in payload.items():
        setattr(rule, field, value)
    rule.destination_type = (rule.destination_type or "global").lower()
    rule.charge_type = (rule.charge_type or "flat").lower()
    rule.payment_provider = (rule.payment_provider or "").strip().lower() or None
    validate_shipping_rule_values(rule)
    rule.updated_by_id = current_user.id
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/shipping/rules/{rule_id}", response_model=dict)
async def delete_shipping_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    rule = await _get_shipping_rule_or_404(db, rule_id, current_user.company_id)
    rule.is_active = False
    rule.is_enabled = False
    rule.updated_by_id = current_user.id
    db.add(rule)
    await db.commit()
    return {"ok": True}


@router.put("/payment-gateways/{gateway_id}", response_model=schemas.StorePaymentGateway)
async def update_payment_gateway(
    *,
    db: AsyncSession = Depends(get_db),
    gateway_id: uuid.UUID,
    gateway_in: schemas.StorePaymentGatewayUpdate,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    gateway = await _get_payment_gateway_or_404(db, gateway_id, current_user.company_id)
    for field, value in gateway_in.model_dump(exclude_unset=True).items():
        if field == "secret_key_encrypted" and not value:
            continue
        if field == "extra_config" and value is not None:
            value = {**(gateway.extra_config or {}), **value}
        setattr(gateway, field, value)
    gateway.updated_by_id = current_user.id
    db.add(gateway)
    await db.commit()
    await db.refresh(gateway)
    return _serialize_admin_payment_gateway(gateway)


@router.get("/public/{storefront_id}/assets/{asset_path:path}")
async def read_public_storefront_asset(
    storefront_id: uuid.UUID,
    asset_path: str,
    db: AsyncSession = Depends(get_db),
    preview_token: str | None = None,
) -> FileResponse:
    """Serve only image files referenced by this storefront or its preview draft."""
    storefront = await _get_public_storefront_by_id(db, storefront_id, preview_token)
    asset_url, file_path = _resolve_public_asset_path(asset_path)
    if not await _public_asset_is_referenced(db, storefront, asset_url, preview_token):
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(
        file_path,
        media_type=mimetypes.guess_type(file_path.name)[0] or "application/octet-stream",
        headers={
            "Cache-Control":
                "private, no-store" if preview_token else "public, max-age=31536000, immutable"
        },
    )


@router.get("/public/by-subdomain/{subdomain}", response_model=schemas.PublicStorefront)
async def read_public_storefront_by_subdomain(
    subdomain: str,
    db: AsyncSession = Depends(get_db),
    preview_token: str | None = None,
) -> Any:
    storefront = await _get_public_storefront_by_subdomain(db, subdomain, preview_token)
    company = await _get_company_for_storefront(db, storefront)
    return schemas.PublicStorefront(
        id=storefront.id,
        name=storefront.name,
        slug=storefront.slug,
        subdomain=storefront.subdomain,
        theme_key=storefront.theme_key,
        theme_settings=storefront.theme_settings or {},
        theme_document=await _published_theme_document(db, storefront),
        theme_documents=await _published_theme_documents(db, storefront),
        checkout_settings=normalize_checkout_settings(storefront.checkout_settings, storefront.theme_settings),
        seo_settings=storefront.seo_settings or {},
        currency=storefront.currency,
        language=storefront.language,
        branding=_serialize_public_branding(storefront, company),
    )


@router.get("/public/by-domain/{domain}", response_model=schemas.PublicStorefront)
async def read_public_storefront_by_domain(
    domain: str,
    db: AsyncSession = Depends(get_db),
    preview_token: str | None = None,
) -> Any:
    storefront = await _get_public_storefront_by_domain(db, domain, preview_token)
    company = await _get_company_for_storefront(db, storefront)
    return schemas.PublicStorefront(
        id=storefront.id,
        name=storefront.name,
        slug=storefront.slug,
        subdomain=storefront.subdomain,
        theme_key=storefront.theme_key,
        theme_settings=storefront.theme_settings or {},
        theme_document=await _published_theme_document(db, storefront),
        theme_documents=await _published_theme_documents(db, storefront),
        checkout_settings=normalize_checkout_settings(storefront.checkout_settings, storefront.theme_settings),
        seo_settings=storefront.seo_settings or {},
        currency=storefront.currency,
        language=storefront.language,
        branding=_serialize_public_branding(storefront, company),
    )


@router.get("/public/certificate-authorization")
async def authorize_storefront_certificate(
    domain: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Caddy on-demand TLS callback. Never authorize an unverified hostname."""
    try:
        host = _normalize_custom_domain(domain)
    except HTTPException:
        raise HTTPException(status_code=404, detail="Unknown storefront")

    platform_domain, _ = _platform_storefront_host_and_port()
    if platform_domain and host.endswith(f".{platform_domain}"):
        subdomain = host[: -(len(platform_domain) + 1)]
        await _get_storefront_for_certificate_by_subdomain(db, subdomain)
    else:
        await _get_storefront_for_certificate_by_domain(db, host)
    return {"ok": True}


@router.get("/public/{storefront_id}", response_model=schemas.PublicStorefront)
async def read_public_storefront(
    storefront_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    preview_token: str | None = None,
) -> Any:
    storefront = await _get_public_storefront_by_id(db, storefront_id, preview_token)
    company = await _get_company_for_storefront(db, storefront)
    return schemas.PublicStorefront(
        id=storefront.id,
        name=storefront.name,
        slug=storefront.slug,
        subdomain=storefront.subdomain,
        theme_key=storefront.theme_key,
        theme_settings=storefront.theme_settings or {},
        theme_document=await _published_theme_document(db, storefront),
        theme_documents=await _published_theme_documents(db, storefront),
        checkout_settings=normalize_checkout_settings(storefront.checkout_settings, storefront.theme_settings),
        seo_settings=storefront.seo_settings or {},
        currency=storefront.currency,
        language=storefront.language,
        branding=_serialize_public_branding(storefront, company),
    )


@router.get("/public/{storefront_id}/shipping/config", response_model=schemas.PublicShippingConfig)
async def read_public_shipping_config(
    storefront_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    preview_token: str | None = None,
) -> Any:
    storefront = await _get_public_storefront_by_id(db, storefront_id, preview_token)
    created = await ensure_default_shipping_configuration(db, storefront)
    if created:
        await db.commit()
    destinations_result = await db.execute(
        select(StorefrontShippingDestination).where(
            StorefrontShippingDestination.storefront_id == storefront.id,
            StorefrontShippingDestination.is_active == True,
        ).order_by(StorefrontShippingDestination.sort_order.asc(), StorefrontShippingDestination.state_name.asc(), StorefrontShippingDestination.city_name.asc())
    )
    methods_result = await db.execute(
        select(StorefrontShippingMethod).where(
            StorefrontShippingMethod.storefront_id == storefront.id,
            StorefrontShippingMethod.is_active == True,
            StorefrontShippingMethod.is_enabled == True,
        ).order_by(StorefrontShippingMethod.sort_order.asc(), StorefrontShippingMethod.name.asc())
    )
    return schemas.PublicShippingConfig(
        destinations=[schemas.PublicShippingDestination.model_validate(item) for item in destinations_result.scalars().all()],
        methods=[schemas.PublicShippingMethod.model_validate(item) for item in methods_result.scalars().all()],
    )


@router.post("/public/{storefront_id}/auth/register", response_model=schemas.PublicStorefrontAuthResponse)
@limiter.limit("5/minute")
async def register_public_storefront_account(
    request: Request,
    storefront_id: uuid.UUID,
    payload: schemas.PublicStorefrontRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    storefront = await _get_public_storefront_by_id(db, storefront_id)
    email = payload.email.strip().lower()

    existing = await db.execute(
        select(StorefrontCustomerAccount).where(
            StorefrontCustomerAccount.storefront_id == storefront.id,
            func.lower(StorefrontCustomerAccount.email) == email,
        )
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="The email is already registered")

    client_result = await db.execute(
        select(Client).where(
            Client.company_id == storefront.company_id,
            func.lower(Client.email) == email,
            Client.is_active == True,
        )
    )
    client = client_result.scalars().first()
    if not client:
        client = Client(
            name=payload.full_name.strip(),
            email=email,
            status="active",
            notes="Created from storefront registration",
            company_id=storefront.company_id,
        )
        db.add(client)
        await db.flush()
    else:
        client.name = payload.full_name.strip()

    account = StorefrontCustomerAccount(
        storefront_id=storefront.id,
        client_id=client.id,
        email=email,
        hashed_password=security.get_password_hash(payload.password),
        full_name=payload.full_name.strip(),
        company_id=storefront.company_id,
        is_active=True,
    )
    db.add(account)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="The email is already registered") from exc
    await db.refresh(account)

    return schemas.PublicStorefrontAuthResponse(
        access_token=_create_storefront_access_token(account, storefront),
        token_type="bearer",
        user=_serialize_public_account_user(account),
    )


@router.post("/public/{storefront_id}/auth/login", response_model=schemas.PublicStorefrontAuthResponse)
@limiter.limit("8/minute")
async def login_public_storefront_account(
    request: Request,
    storefront_id: uuid.UUID,
    payload: schemas.PublicStorefrontLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    storefront = await _get_public_storefront_by_id(db, storefront_id)

    result = await db.execute(
        select(StorefrontCustomerAccount).where(
            StorefrontCustomerAccount.storefront_id == storefront.id,
            func.lower(StorefrontCustomerAccount.email) == payload.email.strip().lower(),
            StorefrontCustomerAccount.is_active == True,
        )
    )
    account = result.scalars().first()
    if not account or not security.verify_password(payload.password, account.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    return schemas.PublicStorefrontAuthResponse(
        access_token=_create_storefront_access_token(account, storefront),
        token_type="bearer",
        user=_serialize_public_account_user(account),
    )


@router.post("/public/{storefront_id}/auth/password-recovery", response_model=schemas.Msg)
@limiter.limit("3/minute")
async def recover_public_storefront_account_password(
    request: Request,
    storefront_id: uuid.UUID,
    payload: schemas.PublicStorefrontPasswordRecoveryRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    storefront = await _get_public_storefront_by_id(db, storefront_id)
    result = await db.execute(
        select(StorefrontCustomerAccount).where(
            StorefrontCustomerAccount.storefront_id == storefront.id,
            func.lower(StorefrontCustomerAccount.email) == payload.email.strip().lower(),
            StorefrontCustomerAccount.is_active == True,
        )
    )
    account = result.scalars().first()

    if account:
        reset_token = auth.create_access_token(
            data={
                "sub": str(account.id),
                "customer_account_id": str(account.id),
                "type": "storefront_reset",
                "storefront_id": str(storefront.id),
                "scope": "storefront",
            },
            expires_delta=timedelta(hours=1),
        )
        await EmailService.send_storefront_reset_password_email(
            email_to=account.email,
            token=reset_token,
            storefront_name=storefront.name,
            reset_link=_storefront_reset_link(storefront, reset_token),
        )

    return schemas.Msg(msg="If the email exists, a recovery email has been sent.")


@router.post("/public/{storefront_id}/auth/reset-password", response_model=schemas.Msg)
@limiter.limit("5/minute")
async def reset_public_storefront_account_password(
    request: Request,
    storefront_id: uuid.UUID,
    payload: schemas.PublicStorefrontPasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    storefront = await _get_public_storefront_by_id(db, storefront_id)
    try:
        token_payload = auth.jwt.decode(payload.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        account_id = token_payload.get("customer_account_id") or token_payload.get("sub")
        token_type = token_payload.get("type")
        token_storefront_id = token_payload.get("storefront_id")
        scope = token_payload.get("scope")
        if (
            not account_id
            or token_type != "storefront_reset"
            or scope != "storefront"
            or token_storefront_id != str(storefront.id)
        ):
            raise HTTPException(status_code=400, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    try:
        account_uuid = uuid.UUID(str(account_id))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    result = await db.execute(
        select(StorefrontCustomerAccount).where(
            StorefrontCustomerAccount.id == account_uuid,
            StorefrontCustomerAccount.storefront_id == storefront.id,
            StorefrontCustomerAccount.is_active == True,
        )
    )
    account = result.scalars().first()
    if not account:
        raise HTTPException(status_code=404, detail="Storefront account not found")

    account.hashed_password = security.get_password_hash(payload.new_password)
    db.add(account)
    await db.commit()
    return schemas.Msg(msg="Password updated successfully")


@router.get("/public/{storefront_id}/account/me", response_model=schemas.PublicStorefrontAccountUser)
async def read_public_storefront_account_me(
    storefront_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_account: StorefrontCustomerAccount = Depends(auth.get_current_storefront_customer),
) -> Any:
    _, account = await _get_current_storefront_customer(storefront_id, db, current_account)
    return _serialize_public_account_user(account)


@router.put("/public/{storefront_id}/account/profile", response_model=schemas.PublicStorefrontAccountUser)
async def update_public_storefront_account_profile(
    storefront_id: uuid.UUID,
    payload: schemas.PublicStorefrontAccountProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_account: StorefrontCustomerAccount = Depends(auth.get_current_storefront_customer),
) -> Any:
    _, account = await _get_current_storefront_customer(storefront_id, db, current_account)
    account.full_name = payload.full_name.strip()
    if account.client_id:
        client = await db.get(Client, account.client_id)
        if client:
            client.name = account.full_name
            db.add(client)
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return _serialize_public_account_user(account)


@router.put("/public/{storefront_id}/account/password", response_model=schemas.Msg)
@limiter.limit("5/minute")
async def change_public_storefront_account_password(
    request: Request,
    storefront_id: uuid.UUID,
    payload: schemas.PublicStorefrontAccountPasswordChange,
    db: AsyncSession = Depends(get_db),
    current_account: StorefrontCustomerAccount = Depends(auth.get_current_storefront_customer),
) -> Any:
    _, account = await _get_current_storefront_customer(storefront_id, db, current_account)
    if not security.verify_password(payload.current_password, account.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="New password must be different")

    account.hashed_password = security.get_password_hash(payload.new_password)
    db.add(account)
    await db.commit()
    return schemas.Msg(msg="Password updated successfully")


@router.get("/public/{storefront_id}/account/orders", response_model=List[schemas.PublicStorefrontAccountOrder])
async def read_public_storefront_account_orders(
    storefront_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_account: StorefrontCustomerAccount = Depends(auth.get_current_storefront_customer),
) -> Any:
    storefront, account = await _get_current_storefront_customer(storefront_id, db, current_account)
    result = await db.execute(
        select(StorefrontOrder)
        .options(
            selectinload(StorefrontOrder.sale)
            .selectinload(Sale.items)
            .selectinload(SaleItem.product)
        )
        .where(
            StorefrontOrder.storefront_id == storefront.id,
            StorefrontOrder.company_id == storefront.company_id,
            StorefrontOrder.is_active == True,
            or_(
                StorefrontOrder.customer_account_id == account.id,
                StorefrontOrder.customer_email == account.email.lower(),
            ),
        )
        .order_by(StorefrontOrder.created_at.desc())
    )
    storefront_orders = result.scalars().unique().all()

    orders: list[schemas.PublicStorefrontAccountOrder] = []
    seen_sale_ids: set[uuid.UUID] = set()
    for storefront_order in storefront_orders:
        sale = storefront_order.sale
        if not sale:
            continue
        seen_sale_ids.add(sale.id)
        first_title = sale.items[0].product.name if sale.items and sale.items[0].product else "Order"
        orders.append(
            schemas.PublicStorefrontAccountOrder(
                order_id=sale.id,
                order_code=str(sale.id).split("-")[0].upper(),
                created_at=sale.created_at,
                status=_map_sale_status_to_order_status(sale.status),
                title=first_title,
                total=float(sale.total or 0.0),
                currency=storefront.currency,
                shipping_line1=storefront_order.shipping_line1,
                shipping_city=storefront_order.shipping_city,
                shipping_state=storefront_order.shipping_state,
                shipping_country=storefront_order.shipping_country,
                shipping_postal_code=storefront_order.shipping_postal_code,
            )
        )

    legacy_result = await db.execute(
        select(Sale)
        .options(selectinload(Sale.items).selectinload(SaleItem.product))
        .where(
            Sale.company_id == storefront.company_id,
            Sale.notes.ilike(f"%storefront_id={storefront.id}%"),
            Sale.notes.ilike(f"%<{account.email}>%"),
            Sale.is_active == True,
        )
        .order_by(Sale.created_at.desc())
    )
    for sale in legacy_result.scalars().unique().all():
        if sale.id in seen_sale_ids:
            continue
        first_title = sale.items[0].product.name if sale.items and sale.items[0].product else "Order"
        orders.append(
            schemas.PublicStorefrontAccountOrder(
                order_id=sale.id,
                order_code=str(sale.id).split("-")[0].upper(),
                created_at=sale.created_at,
                status=_map_sale_status_to_order_status(sale.status),
                title=first_title,
                total=float(sale.total or 0.0),
                currency=storefront.currency,
                shipping_line1=_extract_note_value(sale.notes, "address"),
                shipping_city=_extract_note_value(sale.notes, "city"),
                shipping_state=_extract_note_value(sale.notes, "state"),
                shipping_country=_extract_note_value(sale.notes, "country"),
                shipping_postal_code=_extract_note_value(sale.notes, "postal_code"),
            )
        )

    orders.sort(key=lambda order: order.created_at, reverse=True)
    return orders


@router.post("/public/{storefront_id}/contact", response_model=schemas.Msg)
@limiter.limit("5/minute")
async def send_public_storefront_contact_message(
    request: Request,
    storefront_id: uuid.UUID,
    payload: schemas.PublicStorefrontContactRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    storefront = await _get_public_storefront_by_id(db, storefront_id)
    company = await _get_company_for_storefront(db, storefront)
    branding = _serialize_public_branding(storefront, company)
    destination = branding.support_email or (company.email if company else None)

    if not destination:
        raise HTTPException(status_code=503, detail="Storefront support email is not configured")

    full_name = f"{payload.first_name.strip()} {payload.last_name.strip()}".strip()
    subject = payload.subject.strip() if payload.subject else f"Contact form from {storefront.name}"
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif;">
        <div style="max-width: 640px; margin: 0 auto; padding: 24px;">
          <h2 style="color: #1a237e;">{storefront.name} Contact Message</h2>
          <p><strong>Name:</strong> {full_name}</p>
          <p><strong>Email:</strong> {payload.email}</p>
          <p><strong>Phone:</strong> {payload.phone or "-"}</p>
          <p><strong>Subject:</strong> {subject}</p>
          <hr />
          <p style="white-space: pre-wrap;">{payload.message.strip()}</p>
        </div>
      </body>
    </html>
    """
    await EmailService.send_email(destination, subject, html_content)
    return schemas.Msg(msg="Your message has been sent successfully")


@router.post("/public/{storefront_id}/newsletter", response_model=schemas.Msg)
@limiter.limit("5/minute")
async def subscribe_public_storefront_newsletter(
    request: Request,
    storefront_id: uuid.UUID,
    payload: schemas.PublicNewsletterSubscriptionRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    storefront = await _get_public_storefront_by_id(db, storefront_id)
    email = str(payload.email).strip().lower()
    subscription = await db.scalar(
        select(StorefrontNewsletterSubscription).where(
            StorefrontNewsletterSubscription.storefront_id == storefront.id,
            StorefrontNewsletterSubscription.email == email,
        )
    )

    if subscription:
        if not subscription.is_active:
            subscription.is_active = True
            subscription.subscribed_at = datetime.utcnow()
            subscription.company_id = storefront.company_id
            db.add(subscription)
            await db.commit()
        return schemas.Msg(msg="Ya estabas registrado. Te mantendremos al tanto.")

    db.add(
        StorefrontNewsletterSubscription(
            storefront_id=storefront.id,
            company_id=storefront.company_id,
            email=email,
            source="home",
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        # A repeated click or concurrent request is still a successful opt-in.
        await db.rollback()

    return schemas.Msg(msg="¡Listo! Te registramos para recibir novedades y ofertas.")


@router.get("/public/{storefront_id}/navigation", response_model=List[schemas.PublicStoreNavigationItem])
async def read_public_navigation(
    storefront_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    preview_token: str | None = None,
) -> Any:
    await _get_public_storefront_by_id(db, storefront_id, preview_token)
    result = await db.execute(
        select(StoreNavigationItem).where(
            StoreNavigationItem.storefront_id == storefront_id,
            StoreNavigationItem.is_active == True,
            StoreNavigationItem.is_visible == True,
        ).order_by(StoreNavigationItem.sort_order.asc(), StoreNavigationItem.created_at.asc())
    )
    return [
        schemas.PublicStoreNavigationItem(
            id=item.id,
            parent_id=item.parent_id,
            label=item.label,
            item_type=item.item_type,
            reference_id=item.reference_id,
            url=item.url,
            sort_order=item.sort_order,
        )
        for item in result.scalars().all()
    ]


@router.get("/public/{storefront_id}/payment-gateways", response_model=List[schemas.PublicStorePaymentGateway])
async def read_public_payment_gateways(
    storefront_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    preview_token: str | None = None,
) -> Any:
    await _get_public_storefront_by_id(db, storefront_id, preview_token)
    result = await db.execute(
        select(StorePaymentGateway).where(
            StorePaymentGateway.storefront_id == storefront_id,
            StorePaymentGateway.is_active == True,
            StorePaymentGateway.is_enabled == True,
            StorePaymentGateway.provider.in_(SUPPORTED_PUBLIC_PAYMENT_PROVIDERS),
        ).order_by(StorePaymentGateway.sort_order.asc(), StorePaymentGateway.display_name.asc())
    )
    gateways = result.scalars().all()
    return [
        schemas.PublicStorePaymentGateway(
            id=gateway.id,
            provider=gateway.provider,
            display_name=gateway.display_name,
            is_sandbox=gateway.is_sandbox,
            sort_order=gateway.sort_order,
            checkout_flow=_gateway_checkout_flow(gateway.provider, gateway.extra_config or {}),
            public_config={
                "redirect_url": (gateway.extra_config or {}).get("redirect_url"),
                "checkout_url": (gateway.extra_config or {}).get("checkout_url"),
                "checkout_icon_url": (gateway.extra_config or {}).get("checkout_icon_url"),
                "checkout_description": (gateway.extra_config or {}).get("checkout_description"),
                "checkout_accent": (gateway.extra_config or {}).get("checkout_accent"),
            },
        )
        for gateway in gateways
    ]


@router.get("/public/{storefront_id}/collections", response_model=List[schemas.PublicCollection])
async def read_public_collections(
    storefront_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    preview_token: str | None = None,
) -> Any:
    await _get_public_storefront_by_id(db, storefront_id, preview_token)
    result = await db.execute(
        select(StoreCollection).where(
            StoreCollection.storefront_id == storefront_id,
            StoreCollection.is_active == True,
            StoreCollection.is_visible == True,
        ).order_by(StoreCollection.sort_order.asc(), StoreCollection.name.asc())
    )
    return [
        schemas.PublicCollection(
            id=collection.id,
            storefront_id=collection.storefront_id,
            name=collection.name,
            slug=collection.slug,
            description=collection.description,
            image_url=collection.image_url,
            is_featured=collection.is_featured,
            products=[],
        )
        for collection in result.scalars().all()
    ]


@router.get("/public/{storefront_id}/collections/{slug}", response_model=schemas.PublicCollection)
async def read_public_collection_detail(
    storefront_id: uuid.UUID,
    slug: str,
    db: AsyncSession = Depends(get_db),
    preview_token: str | None = None,
) -> Any:
    collection = await _get_public_collection_or_404(db, storefront_id, slug, preview_token)
    storefront = await _get_public_storefront_by_id(db, storefront_id, preview_token)
    result = await db.execute(
        select(StoreCollectionProduct)
        .options(
            selectinload(StoreCollectionProduct.published_product)
            .selectinload(PublishedProduct.product)
            .selectinload(Product.images),
            selectinload(StoreCollectionProduct.published_product)
            .selectinload(PublishedProduct.product)
            .selectinload(Product.category),
            selectinload(StoreCollectionProduct.published_product)
            .selectinload(PublishedProduct.product)
            .selectinload(Product.brand),
            selectinload(StoreCollectionProduct.published_product)
            .selectinload(PublishedProduct.product)
            .selectinload(Product.variants),
        )
        .where(
            StoreCollectionProduct.collection_id == collection.id,
            StoreCollectionProduct.is_active == True,
        )
        .order_by(StoreCollectionProduct.sort_order.asc(), StoreCollectionProduct.created_at.asc())
    )
    links = result.scalars().all()
    stock_map = await _get_storefront_stock_map(
        db,
        storefront,
        [link.published_product.product_id for link in links if link.published_product and link.published_product.product],
    )
    pricing_context = await load_price_list_context(
        db,
        storefront.price_list_id,
        [link.published_product.product_id for link in links if link.published_product and link.published_product.product],
    )

    products: list[schemas.PublicProduct] = []
    for link in links:
        published_product = link.published_product
        if (
            not published_product
            or not published_product.is_active
            or not published_product.is_published
            or not published_product.product
            or not _public_product_has_available_stock(published_product.product, stock_map)
        ):
            continue
        products.append(
            _serialize_public_product(
                published_product,
                published_product.product,
                stock_map,
                pricing=resolve_product_pricing(pricing_context, published_product.product),
            )
        )
    return schemas.PublicCollection(
        id=collection.id,
        storefront_id=collection.storefront_id,
        name=collection.name,
        slug=collection.slug,
        description=collection.description,
        image_url=collection.image_url,
        is_featured=collection.is_featured,
        products=products,
    )


async def _read_simple_public_catalog(
    db: AsyncSession,
    storefront: Storefront,
    fulfillment_warehouse: Warehouse,
    *,
    page: int,
    page_size: int,
    sort: str,
) -> schemas.PublicCatalogResponse:
    """Load an unfiltered catalog page without materializing the full catalog."""
    published_product_columns = [
        PublishedProduct.id,
        PublishedProduct.product_id,
        PublishedProduct.custom_title,
        PublishedProduct.seo_title,
        PublishedProduct.seo_description,
        PublishedProduct.slug,
        PublishedProduct.price_override,
        PublishedProduct.compare_at_price,
        PublishedProduct.is_featured,
        PublishedProduct.show_stock,
        PublishedProduct.sort_order,
        PublishedProduct.created_at,
        # The public serializer exposes SEO fallbacks even for compact
        # catalog cards. Load them explicitly so AsyncSession never attempts
        # a deferred lazy load while serializing the response.
        PublishedProduct.seo_title,
        PublishedProduct.seo_description,
    ]
    product_columns = [
        Product.id,
        Product.name,
        Product.image_url,
        Product.product_type,
        Product.price,
        Product.track_inventory,
        Product.category_id,
        Product.brand_id,
    ]
    available_inventory = (
        select(Inventory.id)
        .where(
            Inventory.warehouse_id == fulfillment_warehouse.id,
            Inventory.product_id == Product.id,
            Inventory.quantity > Inventory.reserved_quantity,
        )
        .correlate(Product)
        .exists()
    )
    catalog_filters = [
        PublishedProduct.storefront_id == storefront.id,
        PublishedProduct.is_active == True,
        PublishedProduct.is_published == True,
        Product.is_active == True,
        or_(
            Product.track_inventory.is_(False),
            Product.track_inventory.is_(None),
            available_inventory,
        ),
    ]
    total_products = int(
        await db.scalar(
            select(func.count(PublishedProduct.id))
            .join(Product, PublishedProduct.product_id == Product.id)
            .where(*catalog_filters)
        )
        or 0
    )
    total_pages = max(1, (total_products + page_size - 1) // page_size)
    current_page = min(max(1, page), total_pages)
    order_by = (
        [PublishedProduct.created_at.asc(), PublishedProduct.id.asc()]
        if sort == "oldest"
        else [PublishedProduct.created_at.desc(), PublishedProduct.id.desc()]
    )
    result = await db.execute(
        select(PublishedProduct, Product)
        .options(
            load_only(*published_product_columns),
            load_only(*product_columns),
        )
        .join(Product, PublishedProduct.product_id == Product.id)
        .where(*catalog_filters)
        .order_by(*order_by)
        .offset((current_page - 1) * page_size)
        .limit(page_size)
    )
    rows = result.all()
    published_products: list[PublishedProduct] = []
    products_by_id: dict[uuid.UUID, Product] = {}
    for published_product, product in rows:
        set_committed_value(published_product, "product", product)
        published_products.append(published_product)
        products_by_id[product.id] = product

    product_ids = list(products_by_id)
    variant_by_product: dict[uuid.UUID, list[ProductVariant]] = {}
    if product_ids:
        variants_result = await db.execute(
            select(ProductVariant)
            .options(
                load_only(
                    ProductVariant.id,
                    ProductVariant.product_id,
                    ProductVariant.name,
                    ProductVariant.sku,
                    ProductVariant.barcode,
                    ProductVariant.price_extra,
                    ProductVariant.cost_extra,
                    ProductVariant.price,
                    ProductVariant.cost,
                    ProductVariant.attributes,
                )
            )
            .where(ProductVariant.product_id.in_(product_ids))
        )
        for variant in variants_result.scalars().all():
            variant_by_product.setdefault(variant.product_id, []).append(variant)

    category_ids = {product.category_id for product in products_by_id.values() if product.category_id}
    if category_ids:
        categories_result = await db.execute(
            select(Category)
            .options(load_only(Category.id, Category.name))
            .where(Category.id.in_(category_ids))
        )
        categories_by_id = {category.id: category for category in categories_result.scalars().all()}
    else:
        categories_by_id = {}

    brand_ids = {product.brand_id for product in products_by_id.values() if product.brand_id}
    if brand_ids:
        brands_result = await db.execute(
            select(Brand)
            .options(load_only(Brand.id, Brand.name))
            .where(Brand.id.in_(brand_ids))
        )
        brands_by_id = {brand.id: brand for brand in brands_result.scalars().all()}
    else:
        brands_by_id = {}

    for product in products_by_id.values():
        set_committed_value(product, "variants", variant_by_product.get(product.id, []))
        set_committed_value(product, "category", categories_by_id.get(product.category_id))
        set_committed_value(product, "brand", brands_by_id.get(product.brand_id))

    pricing_context = await load_price_list_context(db, storefront.price_list_id, product_ids)
    pricing_by_product = {
        product_id: resolve_product_pricing(pricing_context, product)
        for product_id, product in products_by_id.items()
    }
    if product_ids:
        images_result = await db.execute(
            select(ProductImage)
            .where(ProductImage.product_id.in_(product_ids))
            .order_by(ProductImage.product_id.asc(), ProductImage.order.asc(), ProductImage.created_at.asc())
        )
        images_by_product: dict[uuid.UUID, list[ProductImage]] = {}
        for image in images_result.scalars().all():
            images_by_product.setdefault(image.product_id, []).append(image)
        for product in products_by_id.values():
            set_committed_value(product, "images", images_by_product.get(product.id, []))

    stock_map = await _get_storefront_stock_map(
        db,
        storefront,
        product_ids,
        warehouse=fulfillment_warehouse,
    )
    return schemas.PublicCatalogResponse(
        items=[
            _serialize_public_product(
                published_product,
                published_product.product,
                stock_map,
                compact=True,
                pricing=pricing_by_product.get(published_product.product_id),
            )
            for published_product in published_products
            if published_product.product
        ],
        total_products=total_products,
        current_page=current_page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/public/{storefront_id}/products", response_model=schemas.PublicCatalogResponse)
async def read_public_products(
    storefront_id: uuid.UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
    collection: str | None = None,
    category: str | None = None,
    brand: str | None = None,
    q: str | None = None,
    type: str | None = None,
    size: str | None = None,
    color: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    sort: str = "latest",
    page: int = 1,
    page_size: int = 12,
    include_facets: bool = True,
    product_ids: str | None = None,
    preview_token: str | None = None,
) -> Any:
    response.headers["Cache-Control"] = (
        "private, no-store" if preview_token else "public, max-age=15, s-maxage=15, stale-while-revalidate=30"
    )
    storefront = await _get_public_storefront_by_id(db, storefront_id, preview_token)
    # Resolve the warehouse once and let PostgreSQL discard tracked products
    # with no available stock before loading variants, facets and collections.
    # The previous in-memory pass loaded the complete catalog and made every
    # page request pay for thousands of out-of-stock products.
    fulfillment_warehouse = await _resolve_storefront_fulfillment_warehouse(db, storefront)

    selected_collections = _parse_multi_query_param(collection)
    selected_categories = _parse_multi_query_param(category)
    selected_brands = [_normalize_catalog_text(item) for item in _parse_multi_query_param(brand)]
    selected_types = [item.upper() for item in _parse_multi_query_param(type)]
    selected_sizes = [item.lower() for item in _parse_multi_query_param(size)]
    selected_colors = [item.lower() for item in _parse_multi_query_param(color)]
    requested_product_ids = _parse_uuid_query_list(product_ids)
    normalized_search = _normalize_catalog_text((q or "").strip())
    normalized_sort = _normalize_catalog_sort(sort)
    current_page = max(1, page)
    safe_page_size = max(1, min(page_size, 48))

    simple_catalog_request = (
        not include_facets
        and not requested_product_ids
        and not selected_collections
        and not selected_categories
        and not selected_brands
        and not normalized_search
        and not selected_types
        and not selected_sizes
        and not selected_colors
        and min_price is None
        and max_price is None
        and normalized_sort in {"latest", "oldest"}
    )
    if simple_catalog_request:
        return await _read_simple_public_catalog(
            db,
            storefront,
            fulfillment_warehouse,
            page=current_page,
            page_size=safe_page_size,
            sort=normalized_sort,
        )

    # Facets are useful for the first render, but recalculating them for every
    # infinite-scroll page adds several full-catalog passes. A continuation
    # request only needs products and pagination metadata.
    load_collection_metadata = include_facets or bool(selected_collections)
    if load_collection_metadata:
        collections_result = await db.execute(
            select(StoreCollection).where(
                StoreCollection.storefront_id == storefront_id,
                StoreCollection.is_active == True,
                StoreCollection.is_visible == True,
            ).order_by(StoreCollection.sort_order.asc(), StoreCollection.name.asc())
        )
        collections = collections_result.scalars().all()
    else:
        collections = []
    collection_name_map = {item.slug: item.name for item in collections}

    published_product_columns = [
        PublishedProduct.id,
        PublishedProduct.product_id,
        PublishedProduct.custom_title,
        PublishedProduct.seo_title,
        PublishedProduct.seo_description,
        PublishedProduct.slug,
        PublishedProduct.price_override,
        PublishedProduct.compare_at_price,
        PublishedProduct.is_featured,
        PublishedProduct.sort_order,
        PublishedProduct.created_at,
        # Keep every field accessed by _serialize_public_product loaded in
        # the async query; deferred SEO columns cause MissingGreenlet errors.
        PublishedProduct.seo_title,
        PublishedProduct.seo_description,
    ]
    product_columns = [
        Product.id,
        Product.name,
        Product.image_url,
        Product.product_type,
        Product.price,
        Product.track_inventory,
        Product.category_id,
        Product.brand_id,
    ]
    if normalized_search:
        # Description fields are only needed to perform the in-memory search
        # refinement. Avoid transferring provider HTML for the normal catalog
        # request, where the card payload never uses it.
        published_product_columns.append(PublishedProduct.custom_description)
        product_columns.append(Product.description)

    published_query = (
        # Keep the catalog pass deliberately narrow. Relationship
        # select-in loading here used to fan out into dozens of 500-row
        # queries for a 3k-product catalog. Variants, brands, categories and
        # collection links are loaded in one compact query each below.
        select(PublishedProduct, Product)
        .options(
            load_only(*published_product_columns),
            load_only(*product_columns),
        )
        .join(Product, PublishedProduct.product_id == Product.id)
        .where(
            PublishedProduct.storefront_id == storefront_id,
            PublishedProduct.is_active == True,
            PublishedProduct.is_published == True,
            Product.is_active == True,
        )
    )
    # Apply the inexpensive, index-backed filters before loading variants and
    # collections. The remaining facet filters (size, color and effective
    # variant price) still run in Python because they depend on JSON variant
    # attributes and storefront overrides.
    if selected_categories:
        published_query = published_query.where(Product.category_id.in_(selected_categories))
    if selected_types:
        published_query = published_query.where(Product.product_type.in_(selected_types))
    if requested_product_ids:
        published_query = published_query.where(PublishedProduct.id.in_(requested_product_ids))
    available_inventory = (
        select(Inventory.id)
        .where(
            Inventory.warehouse_id == fulfillment_warehouse.id,
            Inventory.product_id == Product.id,
            Inventory.quantity > Inventory.reserved_quantity,
        )
        .correlate(Product)
        .exists()
    )
    published_query = published_query.where(
        or_(
            Product.track_inventory.is_(False),
            Product.track_inventory.is_(None),
            available_inventory,
        )
    )
    if normalized_search:
        search_filter = f"%{normalized_search}%"
        normalized_column = lambda column: func.lumefy_unaccent(func.lower(column)).ilike(search_filter)
        published_query = published_query.where(
            or_(
                normalized_column(Product.name),
                normalized_column(Product.sku),
                normalized_column(Product.description),
                Product.brand.has(normalized_column(Brand.name)),
                Product.category.has(normalized_column(Category.name)),
                normalized_column(PublishedProduct.custom_title),
                normalized_column(PublishedProduct.custom_description),
                normalized_column(PublishedProduct.slug),
                Product.variants.any(
                    or_(
                        normalized_column(ProductVariant.name),
                        normalized_column(ProductVariant.sku),
                        normalized_column(ProductVariant.barcode),
                    )
                ),
            )
        )

    published_result = await db.execute(published_query)
    published_rows = published_result.all()
    published_products: list[PublishedProduct] = []
    products_by_id: dict[uuid.UUID, Product] = {}
    for published_product, product in published_rows:
        # Attach the already selected product without marking the relationship
        # dirty. This keeps the existing serializer API while avoiding lazy
        # queries during facet calculation.
        set_committed_value(published_product, "product", product)
        published_products.append(published_product)
        products_by_id[product.id] = product

    product_ids = list(products_by_id)
    variant_by_product: dict[uuid.UUID, list[ProductVariant]] = {}
    if product_ids:
        variants_result = await db.execute(
            select(ProductVariant)
            .options(
                load_only(
                    ProductVariant.id,
                    ProductVariant.product_id,
                    ProductVariant.name,
                    ProductVariant.sku,
                    ProductVariant.barcode,
                    ProductVariant.price_extra,
                    ProductVariant.price,
                    ProductVariant.attributes,
                )
            )
            .where(ProductVariant.product_id.in_(product_ids))
        )
        for variant in variants_result.scalars().all():
            variant_by_product.setdefault(variant.product_id, []).append(variant)

    category_ids = {product.category_id for product in products_by_id.values() if product.category_id}
    categories_by_id: dict[uuid.UUID, Category] = {}
    if category_ids:
        categories_result = await db.execute(
            select(Category)
            .options(load_only(Category.id, Category.name))
            .where(Category.id.in_(category_ids))
        )
        categories_by_id = {category.id: category for category in categories_result.scalars().all()}

    brand_ids = {product.brand_id for product in products_by_id.values() if product.brand_id}
    brands_by_id: dict[uuid.UUID, Brand] = {}
    if brand_ids:
        brands_result = await db.execute(
            select(Brand)
            .options(load_only(Brand.id, Brand.name))
            .where(Brand.id.in_(brand_ids))
        )
        brands_by_id = {brand.id: brand for brand in brands_result.scalars().all()}

    for product in products_by_id.values():
        set_committed_value(product, "variants", variant_by_product.get(product.id, []))
        set_committed_value(product, "category", categories_by_id.get(product.category_id))
        set_committed_value(product, "brand", brands_by_id.get(product.brand_id))

    pricing_context = await load_price_list_context(db, storefront.price_list_id, product_ids)
    pricing_by_product = {
        product_id: resolve_product_pricing(pricing_context, product)
        for product_id, product in products_by_id.items()
    }

    product_collection_map: dict[uuid.UUID, list[str]] = {}
    published_ids = [item.id for item in published_products]
    if published_ids and load_collection_metadata:
        collection_links_result = await db.execute(
            select(StoreCollectionProduct.published_product_id, StoreCollection.slug)
            .join(StoreCollection, StoreCollection.id == StoreCollectionProduct.collection_id)
            .where(
                StoreCollectionProduct.published_product_id.in_(published_ids),
                StoreCollection.storefront_id == storefront_id,
                StoreCollection.is_active == True,
                StoreCollection.is_visible == True,
            )
        )
        for published_product_id, collection_slug in collection_links_result.all():
            slugs = product_collection_map.setdefault(published_product_id, [])
            if collection_slug not in slugs:
                slugs.append(collection_slug)
    for published_product in published_products:
        product_collection_map.setdefault(published_product.id, [])

    # These values are reused by the result filter, price sorting and every
    # facet count. Computing them once avoids walking every variant repeatedly
    # (the old code recalculated them up to seven times per product).
    product_contexts: dict[uuid.UUID, dict[str, Any]] = {}
    for published_product in published_products:
        product = published_product.product
        if not product:
            continue
        sizes_list, colors_list = _extract_variant_facets(product.variants or [])
        brand_name = (product.brand.name if getattr(product, "brand", None) else "") or ""
        category_name = product.category.name if getattr(product, "category", None) else ""
        variant_search_values = tuple(
            _normalize_catalog_text(value)
            for variant in (product.variants or [])
            for value in (variant.name, variant.sku, variant.barcode)
            if value
        )
        product_contexts[published_product.id] = {
            "product": product,
            "collections": product_collection_map.get(published_product.id, []),
            "sizes": sizes_list,
            "colors": colors_list,
            "category_id": str(product.category_id) if product.category_id else "",
            "category_name": category_name,
            "brand_name": brand_name,
            "brand_normalized": _normalize_catalog_text(brand_name),
            "product_type": (product.product_type or "").upper(),
            "unit_price": _public_product_starting_price(
                published_product,
                product,
                pricing_by_product.get(product.id),
            ),
            "search_values": (
                _normalize_catalog_text(product.name),
                _normalize_catalog_text(published_product.custom_title),
                _normalize_catalog_text(published_product.slug),
                _normalize_catalog_text(product.description if normalized_search else ""),
                _normalize_catalog_text(
                    published_product.custom_description if normalized_search else ""
                ),
                _normalize_catalog_text(brand_name),
                _normalize_catalog_text(category_name),
            ),
            "variant_search_values": variant_search_values,
        }

    # Availability is a storefront rule, not a manual publishing action. A
    # product remains manually published, but it is omitted while its
    # fulfillment stock is zero and automatically appears again after a
    # positive inventory sync or a released reservation.
    catalog_stock_map = await _get_storefront_stock_map(
        db,
        storefront,
        [item.product_id for item in published_products],
        warehouse=fulfillment_warehouse,
    )
    available_stock_product_ids = {
        product_id
        for (product_id, _variant_id), quantity in catalog_stock_map.items()
        if quantity > 0
    }
    published_products = [
        item
        for item in published_products
        if (
            item.product is not None
            and (
                not item.product.track_inventory
                or item.product_id in available_stock_product_ids
            )
        )
    ]
    published_product_ids = {item.id for item in published_products}
    product_contexts = {
        published_id: context
        for published_id, context in product_contexts.items()
        if published_id in published_product_ids
    }

    def matches_filters(
        published_product: PublishedProduct,
        *,
        ignore_collection: bool = False,
        ignore_category: bool = False,
        ignore_brand: bool = False,
        ignore_type: bool = False,
        ignore_size: bool = False,
        ignore_color: bool = False,
        ignore_price: bool = False,
    ) -> bool:
        context = product_contexts.get(published_product.id)
        if not context:
            return False
        product_collections = context["collections"]
        sizes_list = context["sizes"]
        colors_list = context["colors"]
        category_id = context["category_id"]
        brand_name = context["brand_name"]
        matches_search = (
            not normalized_search
            or any(
                normalized_search in value
                for value in context["search_values"] + context["variant_search_values"]
            )
        )
        matches_collection = (
            ignore_collection
            or not selected_collections
            or any(slug in product_collections for slug in selected_collections)
        )
        matches_type = (
            ignore_type
            or not selected_types
            or context["product_type"] in selected_types
        )
        matches_category = ignore_category or not selected_categories or category_id in selected_categories
        matches_brand = (
            ignore_brand
            or not selected_brands
            or context["brand_normalized"] in selected_brands
        )
        matches_size = (
            ignore_size
            or not selected_sizes
            or any(item.lower() in selected_sizes for item in sizes_list)
        )
        matches_color = (
            ignore_color
            or not selected_colors
            or any(item.lower() in selected_colors for item in colors_list)
        )
        unit_price = context["unit_price"]
        matches_min = ignore_price or min_price is None or unit_price >= float(min_price)
        matches_max = ignore_price or max_price is None or unit_price <= float(max_price)
        return (
            matches_search
            and matches_collection
            and matches_category
            and matches_brand
            and matches_type
            and matches_size
            and matches_color
            and matches_min
            and matches_max
        )

    filtered_products = [item for item in published_products if matches_filters(item)]
    price_facet_values = (
        [
            product_contexts[item.id]["unit_price"]
            for item in published_products
            if item.id in product_contexts and matches_filters(item, ignore_price=True)
        ]
        if include_facets
        else []
    )
    catalog_min_price = min(price_facet_values, default=0.0)
    catalog_max_price = max(price_facet_values, default=0.0)

    def product_sort_key(item: PublishedProduct) -> Any:
        context = product_contexts.get(item.id)
        unit_price = context["unit_price"] if context else 0.0
        if normalized_sort == "best-selling":
            return (int(bool(item.is_featured)), item.sort_order or 0, item.created_at)
        if normalized_sort == "price-low":
            return (unit_price, item.created_at)
        if normalized_sort == "price-high":
            return (-unit_price, item.created_at)
        if normalized_sort == "oldest":
            return (item.created_at,)
        return (item.created_at,)

    reverse = normalized_sort in {"latest", "best-selling"}
    filtered_products.sort(key=product_sort_key, reverse=reverse)

    total_products = len(filtered_products)
    total_pages = max(1, (total_products + safe_page_size - 1) // safe_page_size)
    current_page = min(current_page, total_pages)
    start_index = (current_page - 1) * safe_page_size
    end_index = start_index + safe_page_size
    paginated_products = filtered_products[start_index:end_index]

    # Images are only needed by the visible page. Loading them as a nested
    # select-in relationship for the complete catalog made every search pay
    # for the image gallery of every published product.
    if paginated_products:
        visible_product_ids = [item.product_id for item in paginated_products]
        images_result = await db.execute(
            select(ProductImage)
            .where(ProductImage.product_id.in_(visible_product_ids))
            .order_by(ProductImage.product_id.asc(), ProductImage.order.asc(), ProductImage.created_at.asc())
        )
        images_by_product: dict[uuid.UUID, list[ProductImage]] = {}
        for image in images_result.scalars().all():
            images_by_product.setdefault(image.product_id, []).append(image)
        for published_product in paginated_products:
            if published_product.product:
                set_committed_value(
                    published_product.product,
                    "images",
                    images_by_product.get(published_product.product_id, []),
                )

    stock_map = catalog_stock_map

    collection_counts: dict[str, int] = {item.slug: 0 for item in collections}
    category_names: dict[str, str] = {}
    category_counts: dict[str, int] = {}
    brand_names: dict[str, str] = {}
    brand_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    size_counts: dict[str, int] = {}
    color_counts: dict[str, int] = {}

    if include_facets:
        for published_product in published_products:
            context = product_contexts.get(published_product.id)
            if not context:
                continue
            product = context["product"]
            if product.category_id and getattr(product, "category", None):
                category_names[str(product.category_id)] = product.category.name
            brand_name = context["brand_name"]
            if brand_name:
                brand_names[context["brand_normalized"]] = brand_name

            if matches_filters(published_product, ignore_collection=True):
                for slug_value in context["collections"]:
                    if slug_value in collection_counts:
                        collection_counts[slug_value] += 1
            if product.category_id and matches_filters(published_product, ignore_category=True):
                category_key = str(product.category_id)
                category_counts[category_key] = category_counts.get(category_key, 0) + 1
            if brand_name and matches_filters(published_product, ignore_brand=True):
                brand_key = context["brand_normalized"]
                brand_counts[brand_key] = brand_counts.get(brand_key, 0) + 1
            if matches_filters(published_product, ignore_type=True):
                product_type_value = context["product_type"] or "OTHER"
                type_counts[product_type_value] = type_counts.get(product_type_value, 0) + 1
            sizes_list, colors_list = context["sizes"], context["colors"]
            if matches_filters(published_product, ignore_size=True):
                for entry in sizes_list:
                    size_counts[entry] = size_counts.get(entry, 0) + 1
            if matches_filters(published_product, ignore_color=True):
                for entry in colors_list:
                    color_counts[entry] = color_counts.get(entry, 0) + 1

    selected_collection_name = ", ".join(
        collection_name_map[slug_value]
        for slug_value in selected_collections
        if slug_value in collection_name_map
    ) or None

    return schemas.PublicCatalogResponse(
        items=[
            _serialize_public_product(
                published_product,
                published_product.product,
                stock_map,
                compact=True,
                pricing=pricing_by_product.get(published_product.product_id),
            )
            for published_product in paginated_products
            if published_product.product
        ],
        categories=[
            schemas.PublicCatalogCategory(
                name=name,
                slug=key,
                products=category_counts.get(key, 0),
                is_refined=key in selected_categories,
            )
            for key, name in sorted(category_names.items(), key=lambda entry: entry[1].lower())
        ] if include_facets else [],
        collections=[
            schemas.PublicCatalogCategory(
                name=item.name,
                slug=item.slug,
                products=collection_counts.get(item.slug, 0),
                is_refined=item.slug in selected_collections,
            )
            for item in collections
        ] if include_facets else [],
        brands=[
            schemas.PublicCatalogFacet(
                value=name,
                products=brand_counts.get(key, 0),
                is_refined=key in selected_brands,
            )
            for key, name in sorted(brand_names.items(), key=lambda entry: entry[1].lower())
        ] if include_facets else [],
        product_types=[
            schemas.PublicCatalogProductType(
                name=_normalize_product_type_label(value),
                value=value,
                products=count,
                is_refined=value in selected_types,
            )
            for value, count in sorted(type_counts.items(), key=lambda entry: entry[0])
        ] if include_facets else [],
        sizes=[
            schemas.PublicCatalogFacet(
                value=value,
                products=count,
                is_refined=value.lower() in selected_sizes,
            )
            for value, count in sorted(size_counts.items(), key=lambda entry: entry[0])
        ] if include_facets else [],
        colors=[
            schemas.PublicCatalogFacet(
                value=value,
                products=count,
                is_refined=value.lower() in selected_colors,
            )
            for value, count in sorted(color_counts.items(), key=lambda entry: entry[0])
        ] if include_facets else [],
        total_products=total_products,
        min_price=catalog_min_price,
        max_price=catalog_max_price,
        current_page=current_page,
        page_size=safe_page_size,
        total_pages=total_pages,
        selected_collection_name=selected_collection_name,
    )


@router.get("/public/{storefront_id}/products/{slug}", response_model=schemas.PublicProduct)
async def read_public_product_detail(
    storefront_id: uuid.UUID,
    slug: str,
    db: AsyncSession = Depends(get_db),
    preview_token: str | None = None,
) -> Any:
    storefront = await _get_public_storefront_by_id(db, storefront_id, preview_token)
    published_product = await _get_public_published_product_or_404(db, storefront_id, slug, preview_token)
    stock_map = await _get_storefront_stock_map(db, storefront, [published_product.product_id])
    pricing_context = await load_price_list_context(db, storefront.price_list_id, [published_product.product_id])
    return _serialize_public_product(
        published_product,
        published_product.product,
        stock_map,
        pricing=resolve_product_pricing(pricing_context, published_product.product),
    )


@router.post("/public/{storefront_id}/checkout/preview", response_model=schemas.PublicCheckoutPreviewResponse)
async def preview_public_checkout(
    storefront_id: uuid.UUID,
    payload: schemas.PublicCheckoutPreviewRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    storefront = await _get_public_storefront_by_id(db, storefront_id)
    rows, subtotal = await _load_checkout_products(db, storefront_id, payload.items)

    discount, shipping_result = await _resolve_public_checkout_adjustments(db, storefront, payload, subtotal, rows)
    shipping = shipping_result.shipping
    tax = _calculate_checkout_tax(storefront, subtotal, discount, shipping)
    total = max(0.0, subtotal - discount + shipping + tax)

    return schemas.PublicCheckoutPreviewResponse(
        currency=storefront.currency,
        items=rows,
        subtotal=subtotal,
        discount=discount,
        shipping=shipping,
        tax=tax,
        total=total,
        total_weight=shipping_result.total_weight,
        shipping_method_id=shipping_result.method.id if shipping_result.method else None,
        shipping_method_name=shipping_result.method.name if shipping_result.method else None,
        shipping_rule_name=shipping_result.rule.name if shipping_result.rule else None,
        shipping_quote_required=shipping_result.quote_required,
        shipping_requires_destination=shipping_result.requires_destination,
    )


@router.post("/public/{storefront_id}/checkout/orders", response_model=schemas.PublicCheckoutCreateOrderResponse)
async def create_public_checkout_order(
    storefront_id: uuid.UUID,
    payload: schemas.PublicCheckoutCreateOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_account: StorefrontCustomerAccount | None = Depends(auth.get_optional_current_storefront_customer),
) -> Any:
    storefront = await _get_public_storefront_by_id(db, storefront_id)
    if current_account and current_account.storefront_id != storefront.id:
        current_account = None
    customer_email = (payload.customer.email or "").strip().lower()
    customer_name = _normalize_checkout_text(payload.customer.full_name)
    address_line1 = _normalize_checkout_text(payload.address.line1)
    payment_provider = (payload.payment_provider or "").strip().lower()
    idempotency_key = _normalize_checkout_text(payload.idempotency_key)

    if not customer_name:
        raise HTTPException(status_code=400, detail="Customer full name is required")
    if not customer_email:
        raise HTTPException(status_code=400, detail="Customer email is required")
    if not address_line1:
        raise HTTPException(status_code=400, detail="Shipping address is required")
    if not payment_provider:
        raise HTTPException(status_code=400, detail="Payment provider is required")

    checkout_settings = storefront.checkout_settings or {}
    account_required = (
        checkout_settings.get("checkout_mode") == "required_account"
        or checkout_settings.get("allow_guest_checkout") is False
    )
    if account_required and not current_account:
        raise HTTPException(status_code=400, detail="Inicia sesión o crea una cuenta para completar esta compra")
    if current_account and current_account.email.lower() != customer_email:
        raise HTTPException(status_code=400, detail="El correo del checkout debe coincidir con tu cuenta")
    if bool(checkout_settings.get("require_phone")) and not _normalize_checkout_text(payload.customer.phone):
        raise HTTPException(status_code=400, detail="Este checkout requiere un teléfono de contacto")

    if idempotency_key:
        existing_result = await db.execute(
            select(StorefrontOrder)
            .options(selectinload(StorefrontOrder.sale))
            .where(
                StorefrontOrder.storefront_id == storefront.id,
                StorefrontOrder.idempotency_key == idempotency_key,
                StorefrontOrder.is_active == True,
            )
        )
        existing_order = existing_result.scalars().first()
        if existing_order and existing_order.sale:
            return _build_checkout_order_response(
                storefront=storefront,
                sale=existing_order.sale,
                payment_provider=existing_order.payment_provider,
                payment_status=existing_order.payment_status,
            )

    gateway = await _get_enabled_gateway_for_storefront(db, storefront_id, payment_provider)
    _validate_gateway_checkout_configuration(gateway)
    rows, subtotal = await _load_checkout_products(db, storefront_id, payload.items)

    discount, shipping_result = await _resolve_public_checkout_adjustments(db, storefront, payload, subtotal, rows)
    shipping = shipping_result.shipping
    if shipping_result.requires_destination:
        raise HTTPException(status_code=400, detail="Selecciona un departamento y una ciudad para calcular el envío")
    tax = _calculate_checkout_tax(storefront, subtotal, discount, shipping)
    total = max(0.0, subtotal - discount + shipping + tax)

    warehouse = await _resolve_storefront_fulfillment_warehouse(db, storefront)
    await _validate_checkout_inventory(db, warehouse.id, rows)
    sale_user = await _resolve_default_user_for_company(db, storefront.company_id)
    storefront_customer_account = current_account or await _get_storefront_customer_account_by_email(
        db, storefront, payload.customer.email
    )
    storefront_client = await _get_or_create_storefront_client(db, storefront, payload)
    if storefront_customer_account and not storefront_customer_account.client_id and storefront_client:
        storefront_customer_account.client_id = storefront_client.id
        db.add(storefront_customer_account)
    buyer_note = payload.notes if bool(checkout_settings.get("enable_order_notes", True)) else None

    sale = Sale(
        branch_id=warehouse.branch_id,
        warehouse_id=warehouse.id,
        user_id=sale_user.id,
        client_id=storefront_client.id if storefront_client else None,
        # A checkout is already a commercial order. Reserve stock immediately
        # so another customer cannot buy the same last unit while payment is
        # pending or a manual transfer is being verified.
        status=SaleStatus.DRAFT,
        payment_method=gateway.provider,
        notes=buyer_note,
        shipping_address=address_line1,
        subtotal=subtotal,
        tax=tax,
        discount=discount,
        shipping_cost=shipping,
        total=total,
        company_id=storefront.company_id,
        created_by_id=sale_user.id,
        updated_by_id=sale_user.id,
    )
    # Initialize the relationship before the first flush. Accessing an
    # unloaded async relationship after flush triggers a synchronous lazy load
    # (MissingGreenlet) while building the order.
    sale.items = [
        SaleItem(
            product_id=row.product_id,
            variant_id=row.variant_id,
            quantity=row.quantity,
            quantity_picked=0.0,
            price=row.unit_price,
            discount=0.0,
            total=row.line_subtotal,
            company_id=storefront.company_id,
            created_by_id=sale_user.id,
            updated_by_id=sale_user.id,
        )
        for row in rows
    ]
    db.add(sale)

    await db.flush()
    await log_sale_event(
        db,
        sale_id=str(sale.id),
        company_id=str(storefront.company_id),
        event_type="ORDER_CREATED",
        title="Pedido recibido",
        description=f"Pedido creado desde la tienda con {gateway.display_name}.",
        status="info",
        provider=gateway.provider,
        metadata={
            "source": "storefront",
            "storefront_id": str(storefront.id),
            "payment_provider": gateway.provider,
        },
    )
    shipping_quote_required = shipping_result.quote_required
    if shipping_quote_required:
        sale.status = SaleStatus.QUOTE
    elif not await _reserve_storefront_sale(db, sale):
        raise HTTPException(status_code=400, detail="El stock ya no está disponible para completar este pedido")

    storefront_order = StorefrontOrder(
            storefront_id=storefront.id,
            sale_id=sale.id,
            idempotency_key=idempotency_key,
            customer_account_id=(
                storefront_customer_account.id if storefront_customer_account else None
            ),
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=payload.customer.phone,
            customer_document_id=payload.customer.document_id,
            shipping_line1=address_line1,
            shipping_city=_normalize_checkout_text(payload.address.city),
            shipping_state=_normalize_checkout_text(payload.address.state),
            shipping_country=_normalize_checkout_text(payload.address.country),
            shipping_postal_code=_normalize_checkout_text(payload.address.postal_code),
            shipping_state_code=_normalize_checkout_text(payload.address.state_code),
            shipping_city_code=_normalize_checkout_text(payload.address.city_code),
            shipping_method_id=shipping_result.method.id if shipping_result.method else None,
            shipping_method_name=shipping_result.method.name if shipping_result.method else None,
            shipping_rule_name=shipping_result.rule.name if shipping_result.rule else None,
            shipping_weight=shipping_result.total_weight,
            shipping_quote_required=shipping_quote_required,
            coupon_code=payload.coupon_code,
            buyer_note=buyer_note,
            payment_provider=gateway.provider,
            payment_status="shipping_quote_required" if shipping_quote_required else "pending",
            currency=storefront.currency,
            fulfillment_warehouse_id=warehouse.id,
            company_id=storefront.company_id,
            created_by_id=sale_user.id,
            updated_by_id=sale_user.id,
    )
    sale.storefront_order = storefront_order
    db.add(storefront_order)

    if not shipping_quote_required:
        db.add(
            Payment(
            sale_id=sale.id,
            method=gateway.provider,
            amount=total,
            reference=None,
            company_id=storefront.company_id,
            created_by_id=sale_user.id,
            updated_by_id=sale_user.id,
            )
        )

    await log_sale_event(
        db,
        sale_id=str(sale.id),
        company_id=str(storefront.company_id),
        event_type="SHIPPING_QUOTE_REQUIRED" if shipping_quote_required else "PAYMENT_PENDING",
        title="Envío pendiente de cotización" if shipping_quote_required else "Pago pendiente",
        description=(
            "La tienda debe confirmar el costo del envío antes de cobrar."
            if shipping_quote_required
            else (
                "La orden se cobrará al momento de la entrega."
                if gateway.provider == "cod"
                else f"Esperando confirmación de {gateway.display_name}."
            )
        ),
        status="quote" if shipping_quote_required else "pending",
        provider=gateway.provider,
    )

    await db.commit()
    await db.refresh(sale)
    return _build_checkout_order_response(
        storefront=storefront,
        sale=sale,
        payment_provider=gateway.provider,
        payment_status="shipping_quote_required" if shipping_quote_required else "pending",
    )


@router.post("/public/{storefront_id}/checkout/payment-intent", response_model=schemas.PublicPaymentIntentResponse)
async def create_public_payment_intent(
    storefront_id: uuid.UUID,
    payload: schemas.PublicPaymentIntentRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    storefront = await _get_public_storefront_by_id(db, storefront_id)
    gateway = await _get_enabled_gateway_for_storefront(db, storefront_id, payload.provider)

    order_result = await db.execute(
        select(StorefrontOrder)
        .options(
            selectinload(StorefrontOrder.sale)
            .selectinload(Sale.items)
            .selectinload(SaleItem.product),
        )
        .where(
            StorefrontOrder.storefront_id == storefront.id,
            StorefrontOrder.sale_id == payload.order_id,
            StorefrontOrder.is_active == True,
        )
    )
    storefront_order = order_result.scalars().first()
    if not storefront_order or not storefront_order.sale:
        raise HTTPException(status_code=404, detail="Checkout order not found")
    if storefront_order.shipping_quote_required:
        raise HTTPException(status_code=400, detail="El envío debe ser cotizado antes de iniciar el pago")
    if storefront_order.payment_provider != gateway.provider:
        raise HTTPException(status_code=400, detail="Payment provider does not match the checkout order")
    if storefront_order.payment_status.lower() in {"approved", "approved_partial"}:
        raise HTTPException(status_code=400, detail="This order has already been paid")

    # Never trust client supplied totals. The order was priced server-side from
    # published products, so it is the single source of truth for payment.
    amount = max(0.0, _safe_float(storefront_order.sale.total))
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Order total must be greater than zero")
    currency = (storefront_order.currency or storefront.currency or "USD").upper()

    mode = "sandbox" if gateway.is_sandbox else "production"
    external_reference = str(storefront_order.sale_id)
    metadata = {
        "storefront_id": str(storefront.id),
        "order_id": str(storefront_order.sale_id),
        "customer_email": payload.customer_email,
        "provider": gateway.provider,
    }

    instructions = None
    checkout_url = None
    extra_config = gateway.extra_config or {}
    flow = _gateway_checkout_flow(gateway.provider, extra_config)
    provider_payload: dict[str, Any] = {}

    if gateway.provider == "manual_transfer":
        instructions = extra_config.get("instructions") or "Use bank transfer and validate payment manually."
    elif gateway.provider == "cod":
        instructions = extra_config.get("instructions") or "Paga al recibir tu pedido en la entrega."
    elif gateway.provider == "whatsapp":
        number = "".join(char for char in str(extra_config.get("whatsapp_number") or "") if char.isdigit())
        if len(number) < 8:
            raise HTTPException(status_code=400, detail="WhatsApp requires a valid number in the gateway configuration")
        item_lines = [
            f"- {(item.product.name if item.product else 'Producto')} x{item.quantity:g}"
            for item in storefront_order.sale.items
        ]
        message = "\n".join([
            f"Hola, quiero confirmar mi compra en {storefront.name}.",
            f"Pedido: #{str(storefront_order.sale_id).split('-')[0].upper()}",
            *item_lines,
            f"Total: {currency} {amount:,.0f}",
            f"Cliente: {storefront_order.customer_name}",
            f"Correo: {storefront_order.customer_email}",
            f"Dirección: {storefront_order.shipping_line1}",
        ])
        flow = "whatsapp"
        checkout_url = f"https://wa.me/{number}?text={quote(message)}"
        instructions = extra_config.get("instructions") or "Te llevaremos a WhatsApp para confirmar tu pedido."
    elif gateway.provider == "wompi":
        currency = currency
        if currency != "COP":
            raise HTTPException(status_code=400, detail="Wompi checkout currently supports COP only")

        integrity_secret = (
            extra_config.get("integrity_secret")
            or gateway.secret_key_encrypted
            or extra_config.get("events_secret")
        )
        if not gateway.public_key or not integrity_secret:
            raise HTTPException(status_code=400, detail="Wompi gateway is missing public key or integrity secret")

        amount_in_cents = int(round(amount * 100))
        signature_raw = f"{external_reference}{amount_in_cents}{currency}{integrity_secret}"
        signature = hashlib.sha256(signature_raw.encode("utf-8")).hexdigest()
        redirect_url = (
            payload.return_url
            or extra_config.get("redirect_url")
            or f"{settings.FRONTEND_URL.rstrip('/')}/checkout/success"
        )
        checkout_url = "https://checkout.wompi.co/p/"
        provider_payload = {
            "method": "GET",
            "action": checkout_url,
            "fields": {
                "public-key": gateway.public_key,
                "currency": currency,
                "amount-in-cents": str(amount_in_cents),
                "reference": external_reference,
                "signature:integrity": signature,
                "redirect-url": redirect_url,
            },
        }

        if payload.customer_email:
            provider_payload["fields"]["customer-data:email"] = payload.customer_email
        if payload.customer_full_name:
            provider_payload["fields"]["customer-data:full-name"] = payload.customer_full_name
        if payload.customer_phone:
            provider_payload["fields"]["customer-data:phone-number"] = payload.customer_phone
            provider_payload["fields"]["customer-data:phone-number-prefix"] = "+57"

        shipping_address = payload.shipping_address or {}
        if shipping_address.get("line1"):
            provider_payload["fields"]["shipping-address:address-line-1"] = str(shipping_address["line1"])
        if shipping_address.get("country"):
            provider_payload["fields"]["shipping-address:country"] = str(shipping_address["country"]).upper()
        if shipping_address.get("city"):
            provider_payload["fields"]["shipping-address:city"] = str(shipping_address["city"])
        if shipping_address.get("state"):
            provider_payload["fields"]["shipping-address:region"] = str(shipping_address["state"])
        if shipping_address.get("phone"):
            provider_payload["fields"]["shipping-address:phone-number"] = str(shipping_address["phone"])
        if payload.customer_full_name:
            provider_payload["fields"]["shipping-address:name"] = payload.customer_full_name
    elif gateway.provider == "payu":
        account_id = str(extra_config.get("account_id") or "").strip()
        api_key = gateway.secret_key_encrypted or str(extra_config.get("api_key") or "").strip()
        if not gateway.merchant_id or not account_id or not api_key:
            if not gateway.is_sandbox:
                raise HTTPException(status_code=400, detail="PayU requires merchant ID, account ID and API key")
            flow = "external_redirect"
            checkout_url = payload.return_url or f"{settings.FRONTEND_URL.rstrip('/')}/checkout/success"
            instructions = "Simulación PayU: configura merchant ID, account ID y API key para enviar pagos reales."
        else:
            # Keep the complete UUID in the provider reference. A shortened
            # UUID cannot be safely resolved by an asynchronous confirmation.
            reference_code = f"LUMEFY-{storefront_order.sale_id}"
            amount_value = f"{amount:.2f}"
            signature = hashlib.md5(
                f"{api_key}~{gateway.merchant_id}~{reference_code}~{amount_value}~{currency}".encode("utf-8")
            ).hexdigest()
            checkout_url = (
                "https://sandbox.checkout.payulatam.com/ppp-web-gateway-payu/"
                if gateway.is_sandbox else "https://checkout.payulatam.com/ppp-web-gateway-payu/"
            )
            flow = "form_redirect"
            provider_payload = {
                "method": "POST",
                "action": checkout_url,
                "fields": {
                    "merchantId": str(gateway.merchant_id), "accountId": account_id,
                    "description": f"Pedido {reference_code}", "referenceCode": reference_code,
                    "amount": amount_value, "tax": "0", "taxReturnBase": "0",
                    "currency": currency, "signature": signature,
                    "test": "1" if gateway.is_sandbox else "0",
                    "buyerEmail": storefront_order.customer_email,
                    "responseUrl": payload.return_url or f"{settings.FRONTEND_URL.rstrip('/')}/checkout/success",
                },
            }
            confirmation_url = str(extra_config.get("confirmation_url") or "").strip()
            if confirmation_url:
                provider_payload["fields"]["confirmationUrl"] = confirmation_url.replace(
                    "{storefront_id}", str(storefront.id)
                )
    elif gateway.provider == "mercadopago":
        access_token = gateway.secret_key_encrypted or str(extra_config.get("access_token") or "").strip()
        if not access_token:
            if not gateway.is_sandbox:
                raise HTTPException(status_code=400, detail="Mercado Pago requires an access token")
            flow = "external_redirect"
            checkout_url = payload.return_url or f"{settings.FRONTEND_URL.rstrip('/')}/checkout/success"
            instructions = "Simulación Mercado Pago: configura el access token para crear preferencias reales."
        else:
            preference = {
                "items": [{
                    "title": item.product.name if item.product else "Producto",
                    "quantity": int(item.quantity),
                    "unit_price": float(item.price),
                    "currency_id": currency,
                } for item in storefront_order.sale.items],
                "external_reference": external_reference,
                "payer": {"email": storefront_order.customer_email},
                "back_urls": {"success": payload.return_url, "pending": payload.return_url, "failure": payload.return_url},
                "auto_return": "approved",
            }
            notification_url = str(extra_config.get("notification_url") or "").strip()
            if notification_url:
                preference["notification_url"] = notification_url.replace("{storefront_id}", str(storefront.id))
            response = requests.post(
                "https://api.mercadopago.com/checkout/preferences",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json=preference,
                timeout=15,
            )
            if response.status_code >= 400:
                raise HTTPException(status_code=400, detail="Mercado Pago could not create the checkout preference")
            result = response.json() or {}
            checkout_url = result.get("sandbox_init_point") if gateway.is_sandbox else result.get("init_point")
            if not checkout_url:
                raise HTTPException(status_code=400, detail="Mercado Pago did not return a checkout URL")
            flow = "external_redirect"
    elif gateway.provider == "addi":
        if currency != "COP":
            raise HTTPException(status_code=400, detail="Addi checkout only supports COP")
        client_id = str(gateway.public_key or "").strip()
        client_secret = str(gateway.secret_key_encrypted or "").strip()
        callback_url = str(extra_config.get("callback_url") or "").strip().replace(
            "{storefront_id}", str(storefront.id)
        )
        callback_username = str(extra_config.get("callback_username") or "").strip()
        callback_password = str(extra_config.get("callback_password") or "").strip()
        document_id = "".join(char for char in str(storefront_order.customer_document_id or "") if char.isdigit())
        phone = "".join(char for char in str(storefront_order.customer_phone or "") if char.isdigit())
        if phone.startswith("57") and len(phone) > 10:
            phone = phone[2:]
        if not client_id or not client_secret:
            if not gateway.is_sandbox:
                raise HTTPException(status_code=400, detail="Addi requires Client ID and Client secret")
            checkout_url = payload.return_url or f"{settings.FRONTEND_URL.rstrip('/')}/checkout/success"
            flow = "external_redirect"
            instructions = "Simulación Addi: configura Client ID, Client secret y callback para iniciar un crédito real."
        elif not document_id or not phone or not callback_url or not callback_username or not callback_password:
            raise HTTPException(
                status_code=400,
                detail="Addi requiere documento CC, teléfono y configuración completa de callback para continuar",
            )
        else:
            auth_base = "https://auth.addi-staging.com" if gateway.is_sandbox else "https://auth.addi.com"
            api_base = "https://api.addi-staging.com" if gateway.is_sandbox else "https://api.addi.com"
            audience = str(extra_config.get("audience") or (
                "https://api.staging.addi.com" if gateway.is_sandbox else "https://api.addi.com"
            )).strip()
            auth_response = requests.post(
                f"{auth_base}/oauth/token",
                json={
                    "audience": audience,
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                timeout=15,
            )
            if auth_response.status_code >= 400 or not (auth_response.json() or {}).get("access_token"):
                raise HTTPException(status_code=400, detail="Addi could not authenticate the configured merchant")
            access_token = str((auth_response.json() or {}).get("access_token"))
            name_parts = [part for part in storefront_order.customer_name.split() if part]
            first_name = " ".join(name_parts[:2]) or storefront_order.customer_name
            last_name = " ".join(name_parts[2:]) or "-"
            country = (storefront_order.shipping_country or "CO").upper()
            redirection_url = payload.return_url or f"{settings.FRONTEND_URL.rstrip('/')}/checkout/success"
            application = {
                "orderId": str(storefront_order.sale_id),
                "totalAmount": f"{amount:.2f}",
                "shippingAmount": f"{_safe_float(storefront_order.sale.shipping_cost):.2f}",
                "totalTaxesAmount": f"{_safe_float(storefront_order.sale.tax):.2f}",
                "currency": currency,
                "items": [
                    {
                        "sku": str(item.product.sku or item.product_id) if item.product else str(item.product_id),
                        "name": item.product.name if item.product else "Producto",
                        "quantity": str(int(item.quantity)),
                        "unitPrice": f"{_safe_float(item.price):.2f}",
                        "tax": "0.00",
                    }
                    for item in storefront_order.sale.items
                ],
                "client": {
                    "idType": "CC",
                    "idNumber": document_id,
                    "firstName": first_name,
                    "lastName": last_name,
                    "email": storefront_order.customer_email,
                    "cellphone": phone,
                    "cellphoneCountryCode": "+57",
                    "address": {
                        "lineOne": storefront_order.shipping_line1,
                        "city": storefront_order.shipping_city or "Bogotá",
                        "country": country,
                    },
                },
                "shippingAddress": {
                    "lineOne": storefront_order.shipping_line1,
                    "city": storefront_order.shipping_city or "Bogotá",
                    "country": country,
                },
                "billingAddress": {
                    "lineOne": storefront_order.shipping_line1,
                    "city": storefront_order.shipping_city or "Bogotá",
                    "country": country,
                },
                "allyUrlRedirection": {
                    "callbackUrl": callback_url,
                    "redirectionUrl": redirection_url,
                    **({"logoUrl": str(extra_config.get("logo_url"))} if extra_config.get("logo_url") else {}),
                },
            }
            application_response = requests.post(
                f"{api_base}/v1/online-applications",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json=application,
                timeout=20,
                allow_redirects=False,
            )
            checkout_url = application_response.headers.get("Location")
            if application_response.status_code not in {301, 302, 303} or not checkout_url:
                raise HTTPException(status_code=400, detail="Addi could not create the credit application")
            flow = "external_redirect"
    elif gateway.provider == "sistecredito":
        checkout_url = str(extra_config.get("checkout_url") or "").strip()
        if not checkout_url.startswith("https://"):
            if gateway.is_sandbox:
                checkout_url = payload.return_url or f"{settings.FRONTEND_URL.rstrip('/')}/checkout/success"
                instructions = f"Simulación {gateway.display_name}: agrega el checkout entregado por el proveedor para pagos reales."
            else:
                raise HTTPException(status_code=400, detail=f"{gateway.display_name} requires a secure checkout URL in its gateway configuration")
        flow = "external_redirect"
        instructions = instructions or extra_config.get("instructions") or "Serás redirigido para completar el pago."

    await log_sale_event(
        db,
        sale_id=str(storefront_order.sale_id),
        company_id=str(storefront.company_id),
        event_type="PAYMENT_INTENT_CREATED",
        title="Intento de pago preparado",
        description=f"Se preparó el checkout de {gateway.display_name}.",
        status="info",
        provider=gateway.provider,
        reference=external_reference,
        metadata={"flow": flow, "mode": mode},
    )
    await db.commit()

    return schemas.PublicPaymentIntentResponse(
        provider=gateway.provider,
        flow=flow,
        mode=mode,
        amount=amount,
        currency=currency,
        external_reference=external_reference,
        checkout_url=checkout_url,
        public_key=gateway.public_key,
        merchant_id=gateway.merchant_id,
        instructions=instructions,
        metadata=metadata,
        provider_payload=provider_payload,
    )


@router.get("/public/{storefront_id}/checkout/payment-status", response_model=schemas.PublicPaymentStatusResponse)
async def read_public_payment_status(
    storefront_id: uuid.UUID,
    provider: str,
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    storefront = await _get_public_storefront_by_id(db, storefront_id)
    gateway = await _get_enabled_gateway_for_storefront(db, storefront_id, provider)

    clean_provider = (provider or "").strip().lower()
    clean_transaction_id = (transaction_id or "").strip()
    if not clean_transaction_id:
        raise HTTPException(status_code=400, detail="Transaction id is required")

    if clean_provider != "wompi":
        raise HTTPException(status_code=400, detail="Payment status verification is not available for this provider yet")

    mode = "sandbox" if gateway.is_sandbox else "production"
    base_url = "https://sandbox.wompi.co/v1" if gateway.is_sandbox else "https://production.wompi.co/v1"
    response = requests.get(f"{base_url}/transactions/{clean_transaction_id}", timeout=15)
    if response.status_code >= 400:
        raise HTTPException(status_code=400, detail="Could not verify Wompi transaction status")

    payload = response.json() or {}
    data = payload.get("data") or {}
    status = str(data.get("status") or "PENDING").upper()
    external_reference = data.get("reference")
    status_message = data.get("status_message")

    storefront_order = None
    sale = None
    if external_reference:
        try:
            sale_id = uuid.UUID(str(external_reference))
            result = await db.execute(
                select(StorefrontOrder)
                .options(
                    selectinload(StorefrontOrder.sale)
                    .selectinload(Sale.items)
                    .selectinload(SaleItem.product)
                )
                .where(
                    StorefrontOrder.storefront_id == storefront.id,
                    StorefrontOrder.sale_id == sale_id,
                    StorefrontOrder.is_active == True,
                )
            )
            storefront_order = result.scalars().first()
            sale = storefront_order.sale if storefront_order else None
        except ValueError:
            storefront_order = None

    result_status = status
    if storefront_order:
        previous_status = (storefront_order.payment_status or "").lower()
        storefront_order.payment_status = status.lower()
        storefront_order.updated_by_id = storefront_order.updated_by_id or storefront_order.created_by_id
        db.add(storefront_order)

    if sale:
        if status in {"APPROVED", "APPROVED_PARTIAL"}:
            expected_amount_in_cents = int(round(float(sale.total) * 100))
            received_amount_in_cents = data.get("amount_in_cents")
            received_currency = str(data.get("currency") or "").upper()
            if received_amount_in_cents is None or int(received_amount_in_cents) != expected_amount_in_cents:
                raise HTTPException(status_code=400, detail="Wompi transaction amount does not match the order")
            if received_currency and received_currency != (storefront.currency or "COP").upper():
                raise HTTPException(status_code=400, detail="Wompi transaction currency does not match the order")

        payment_result = await db.execute(
            select(Payment).where(
                Payment.sale_id == sale.id,
                Payment.method == gateway.provider,
                Payment.is_active == True,
            )
        )
        payment = payment_result.scalars().first()
        if payment:
            payment.reference = clean_transaction_id
            db.add(payment)

        if status in {"APPROVED", "APPROVED_PARTIAL"}:
            confirmed = await _reserve_storefront_sale(db, sale)
            if not confirmed:
                storefront_order.payment_status = "approved_stock_unavailable"
                result_status = "APPROVED_STOCK_UNAVAILABLE"
                status_message = "Pago aprobado; el pedido requiere revisión por falta de inventario."
        elif status in {"DECLINED", "ERROR", "VOIDED"} and sale.status in {
            SaleStatus.DRAFT,
            SaleStatus.QUOTE,
            SaleStatus.CONFIRMED,
        }:
            await _cancel_storefront_sale_and_release_reservation(db, sale)
        final_status = (storefront_order.payment_status or status).lower()
        if previous_status != final_status:
            await log_sale_event(
                db,
                sale_id=str(sale.id),
                company_id=str(sale.company_id),
                event_type="PAYMENT_STATUS_UPDATED",
                title="Estado de pago verificado",
                description=f"El estado consultado en Wompi es {final_status.upper()}.",
                status="success" if final_status in {"approved", "approved_partial"} else "warning" if final_status in {"declined", "error", "voided"} else "pending",
                provider="wompi",
                reference=clean_transaction_id,
                metadata={"from": previous_status or "none", "to": final_status, "source": "status_api"},
            )
        sale.updated_by_id = sale.updated_by_id or sale.created_by_id
        db.add(sale)
        await db.commit()

    return schemas.PublicPaymentStatusResponse(
        provider=clean_provider,
        transaction_id=clean_transaction_id,
        external_reference=str(external_reference) if external_reference else None,
        status=result_status,
        status_message=status_message or f"Estado consultado en Wompi ({mode})",
        order_id=sale.id if sale else None,
        order_code=str(sale.id).split("-")[0].upper() if sale else None,
    )


@router.post("/public/payments/addi/webhook/{storefront_id}")
async def receive_addi_payment_callback(
    storefront_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Process Addi's Basic-auth callback and echo its body as required by Addi."""
    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid Addi callback payload") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid Addi callback payload")
    gateway = await _get_enabled_gateway_for_storefront(db, storefront_id, "addi")
    config = gateway.extra_config or {}
    if not _has_valid_basic_auth(
        request.headers.get("Authorization"),
        str(config.get("callback_username") or "").strip(),
        str(config.get("callback_password") or "").strip(),
    ):
        raise HTTPException(status_code=401, detail="Invalid Addi callback credentials")
    try:
        sale_id = uuid.UUID(str(payload.get("orderId") or ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Unknown Addi payment reference") from exc
    storefront_order = await _get_storefront_order_for_payment_webhook(db, storefront_id, sale_id, "addi")
    sale = storefront_order.sale
    if str(payload.get("currency") or "").upper() != (storefront_order.currency or "").upper():
        raise HTTPException(status_code=400, detail="Addi transaction currency does not match the order")
    status = str(payload.get("status") or "").upper()
    approved_amount = _safe_float(payload.get("approvedAmount"), -1)
    if status == "APPROVED" and abs(approved_amount - _safe_float(sale.total)) > 0.000001:
        raise HTTPException(status_code=400, detail="Addi approved amount does not match the order")
    status_map = {
        "APPROVED": "approved",
        "REJECTED": "rejected",
        "DECLINED": "declined",
        "ABANDONED": "expired",
        "INTERNAL_ERROR": "declined",
    }
    application_id = str(payload.get("applicationId") or payload.get("orderId"))
    await _apply_gateway_payment_status(db, storefront_order, "addi", status_map.get(status, "pending"), application_id)
    # Addi retries callbacks unless it receives the exact original JSON body.
    return payload


@router.post("/public/payments/payu/webhook/{storefront_id}")
async def receive_payu_payment_confirmation(
    storefront_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Receive and verify PayU's server-to-server form confirmation."""
    form = await request.form()
    payload = {key: value for key, value in form.items()}
    reference_sale = _safe_string(payload.get("reference_sale"))
    if not reference_sale or not reference_sale.upper().startswith("LUMEFY-"):
        raise HTTPException(status_code=400, detail="Unknown PayU payment reference")
    try:
        sale_id = uuid.UUID(reference_sale[len("LUMEFY-"):])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Unknown PayU payment reference") from exc

    storefront_order = await _get_storefront_order_for_payment_webhook(db, storefront_id, sale_id, "payu")
    gateway = await _get_enabled_gateway_for_storefront(db, storefront_id, "payu")
    api_key = gateway.secret_key_encrypted or str((gateway.extra_config or {}).get("api_key") or "").strip()
    if not _has_valid_payu_confirmation_signature(payload, api_key):
        raise HTTPException(status_code=400, detail="Invalid PayU confirmation signature")
    if str(payload.get("merchant_id") or "") != str(gateway.merchant_id or ""):
        raise HTTPException(status_code=400, detail="PayU merchant does not match the configured gateway")

    sale = storefront_order.sale
    try:
        received_amount = Decimal(str(payload.get("value"))).quantize(Decimal("0.01"))
        expected_amount = Decimal(str(sale.total)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid PayU confirmation amount") from exc
    if received_amount != expected_amount:
        raise HTTPException(status_code=400, detail="PayU transaction amount does not match the order")
    if str(payload.get("currency") or "").upper() != (storefront_order.currency or "").upper():
        raise HTTPException(status_code=400, detail="PayU transaction currency does not match the order")

    state = str(payload.get("state_pol") or "")
    status_by_state = {"4": "approved", "5": "expired", "6": "declined"}
    status = status_by_state.get(state, "pending")
    transaction_id = _safe_string(payload.get("transaction_id")) or _safe_string(payload.get("reference_pol"))
    if not transaction_id:
        raise HTTPException(status_code=400, detail="Incomplete PayU confirmation")
    final_status = await _apply_gateway_payment_status(db, storefront_order, "payu", status, transaction_id)
    return {"received": True, "status": final_status}


@router.post("/public/payments/mercadopago/webhook/{storefront_id}")
async def receive_mercadopago_payment_event(
    storefront_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Receive Mercado Pago notifications and verify the payment at its API."""
    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid Mercado Pago webhook payload") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid Mercado Pago webhook payload")

    gateway = await _get_enabled_gateway_for_storefront(db, storefront_id, "mercadopago")
    extra_config = gateway.extra_config or {}
    webhook_secret = str(extra_config.get("webhook_secret") or "").strip()
    if not _has_valid_mercadopago_webhook_signature(
        payload,
        request.headers.get("x-signature"),
        request.headers.get("x-request-id"),
        webhook_secret,
    ):
        raise HTTPException(status_code=400, detail="Invalid Mercado Pago webhook signature")

    data = payload.get("data") or {}
    payment_id = _safe_string(data.get("id") if isinstance(data, dict) else None)
    access_token = gateway.secret_key_encrypted or str(extra_config.get("access_token") or "").strip()
    if not payment_id or not access_token:
        raise HTTPException(status_code=400, detail="Mercado Pago webhook requires a payment ID and access token")
    response = requests.get(
        f"https://api.mercadopago.com/v1/payments/{payment_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=400, detail="Mercado Pago could not verify the payment")
    payment_data = response.json() or {}
    try:
        sale_id = uuid.UUID(str(payment_data.get("external_reference") or ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Unknown Mercado Pago payment reference") from exc

    storefront_order = await _get_storefront_order_for_payment_webhook(db, storefront_id, sale_id, "mercadopago")
    sale = storefront_order.sale
    try:
        received_amount = Decimal(str(payment_data.get("transaction_amount"))).quantize(Decimal("0.01"))
        expected_amount = Decimal(str(sale.total)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid Mercado Pago payment amount") from exc
    if received_amount != expected_amount:
        raise HTTPException(status_code=400, detail="Mercado Pago transaction amount does not match the order")
    if str(payment_data.get("currency_id") or "").upper() != (storefront_order.currency or "").upper():
        raise HTTPException(status_code=400, detail="Mercado Pago transaction currency does not match the order")

    provider_status = str(payment_data.get("status") or "").lower()
    status_map = {
        "approved": "approved",
        "rejected": "rejected",
        "cancelled": "cancelled",
        "refunded": "cancelled",
        "charged_back": "cancelled",
    }
    final_status = await _apply_gateway_payment_status(
        db,
        storefront_order,
        "mercadopago",
        status_map.get(provider_status, "pending"),
        str(payment_data.get("id") or payment_id),
    )
    return {"received": True, "status": final_status}


@router.post("/public/payments/wompi/webhook")
async def receive_wompi_payment_event(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Accept signed Wompi transaction events independently of browser redirects."""
    try:
        event = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid Wompi event payload") from exc
    if not isinstance(event, dict) or event.get("event") != "transaction.updated":
        return {"received": True, "ignored": True}

    transaction = ((event.get("data") or {}).get("transaction") or {})
    if not isinstance(transaction, dict):
        raise HTTPException(status_code=400, detail="Invalid Wompi transaction event")
    try:
        sale_id = uuid.UUID(str(transaction.get("reference") or ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Unknown Wompi payment reference") from exc

    storefront_order = await db.scalar(
        select(StorefrontOrder)
        .options(
            selectinload(StorefrontOrder.sale).selectinload(Sale.items).selectinload(SaleItem.product),
            selectinload(StorefrontOrder.storefront),
        )
        .where(StorefrontOrder.sale_id == sale_id, StorefrontOrder.is_active == True)
    )
    if not storefront_order or not storefront_order.sale or not storefront_order.storefront:
        raise HTTPException(status_code=404, detail="Checkout order not found")
    if storefront_order.payment_provider != "wompi":
        raise HTTPException(status_code=400, detail="Payment provider does not match the checkout order")

    gateway = await _get_enabled_gateway_for_storefront(db, storefront_order.storefront_id, "wompi")
    events_secret = (gateway.extra_config or {}).get("events_secret")
    header_checksum = request.headers.get("X-Event-Checksum")
    if not _has_valid_wompi_event_signature(event, events_secret, header_checksum):
        raise HTTPException(status_code=400, detail="Invalid Wompi event signature")

    status = str(transaction.get("status") or "").upper()
    transaction_id = str(transaction.get("id") or "").strip()
    if not status or not transaction_id:
        raise HTTPException(status_code=400, detail="Incomplete Wompi transaction event")

    sale = storefront_order.sale
    existing_status = (storefront_order.payment_status or "").lower()
    await log_sale_event(
        db,
        sale_id=str(sale.id),
        company_id=str(sale.company_id),
        event_type="PAYMENT_WEBHOOK_RECEIVED",
        title="Webhook de pago recibido",
        description=f"Wompi notificó el estado {status}.",
        status="info",
        provider="wompi",
        reference=transaction_id,
        metadata={"provider_status": status},
    )
    if existing_status in {"approved", "approved_partial"} and status not in {"APPROVED", "APPROVED_PARTIAL"}:
        await db.commit()
        return {"received": True, "ignored": True}

    if status in {"APPROVED", "APPROVED_PARTIAL"}:
        expected_amount = int(round(float(sale.total) * 100))
        if int(transaction.get("amount_in_cents") or -1) != expected_amount:
            raise HTTPException(status_code=400, detail="Wompi transaction amount does not match the order")
        if str(transaction.get("currency") or "").upper() != (storefront_order.currency or "COP").upper():
            raise HTTPException(status_code=400, detail="Wompi transaction currency does not match the order")

    payment = await db.scalar(select(Payment).where(
        Payment.sale_id == sale.id,
        Payment.method == "wompi",
        Payment.is_active == True,
    ))
    if payment:
        payment.reference = transaction_id
        db.add(payment)
    storefront_order.payment_status = status.lower()
    db.add(storefront_order)

    if status in {"APPROVED", "APPROVED_PARTIAL"}:
        if not await _reserve_storefront_sale(db, sale):
            storefront_order.payment_status = "approved_stock_unavailable"
    elif status in {"DECLINED", "ERROR", "VOIDED"} and sale.status in {
        SaleStatus.DRAFT,
        SaleStatus.QUOTE,
        SaleStatus.CONFIRMED,
    }:
        await _cancel_storefront_sale_and_release_reservation(db, sale)
    final_status = (storefront_order.payment_status or status).lower()
    if existing_status != final_status:
        await log_sale_event(
            db,
            sale_id=str(sale.id),
            company_id=str(sale.company_id),
            event_type="PAYMENT_STATUS_UPDATED",
            title="Estado de pago actualizado",
            description=f"El pago quedó en estado {final_status.upper()}.",
            status="success" if final_status in {"approved", "approved_partial"} else "warning" if final_status in {"declined", "error", "voided"} else "pending",
            provider="wompi",
            reference=transaction_id,
            metadata={"from": existing_status or "none", "to": final_status},
        )
    db.add(sale)
    await db.commit()
    return {"received": True}
