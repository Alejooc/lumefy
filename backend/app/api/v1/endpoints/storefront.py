import hashlib
import uuid
from datetime import timedelta
from typing import Any, List
import requests

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import auth, security
from app.core.database import get_db
from app.core.permissions import PermissionChecker
from app.core.plan_limits import PlanLimitChecker
from app.core.config import settings
from app.core.rate_limit import limiter
from app.models.branch import Branch
from app.models.company import Company
from app.models.inventory import Inventory
from app.models.sale import Payment, Sale, SaleItem, SaleStatus
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.user import User
from app.models.client import Client
from app.services.email import EmailService
from app.models.storefront import (
    PublishedProduct,
    StoreCollection,
    StoreCollectionProduct,
    StoreNavigationItem,
    StorePaymentGateway,
    Storefront,
    StorefrontDomain,
    StorefrontOrder,
)
from app.schemas import storefront as schemas

router = APIRouter()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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


def _serialize_public_account_user(user: User) -> schemas.PublicStorefrontAccountUser:
    return schemas.PublicStorefrontAccountUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        created_at=user.created_at,
    )


def _is_storefront_customer(user: User, storefront: Storefront) -> bool:
    return (
        bool(user.is_active)
        and user.company_id == storefront.company_id
        and user.role_id is None
        and not user.is_superuser
    )


async def _get_current_storefront_customer(
    storefront_id: uuid.UUID,
    db: AsyncSession,
    current_user: User,
) -> tuple[Storefront, User]:
    storefront = await _get_public_storefront_by_id(db, storefront_id)
    if not _is_storefront_customer(current_user, storefront):
        raise HTTPException(status_code=403, detail="Storefront account access denied")
    return storefront, current_user


def _create_storefront_access_token(user: User, storefront: Storefront) -> str:
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return auth.create_access_token(
        data={
            "sub": user.email,
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
    )


async def _get_storefront_customer_user_by_email(
    db: AsyncSession,
    storefront: Storefront,
    email: str | None,
) -> User | None:
    normalized_email = _safe_string(email)
    if not normalized_email:
        return None

    result = await db.execute(
        select(User).where(
            User.company_id == storefront.company_id,
            User.email == normalized_email.lower(),
            User.is_active == True,
        )
    )
    user = result.scalars().first()
    if not user or not _is_storefront_customer(user, storefront):
        return None
    return user


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
    return f"{base_url}/password/reset?token={token}&storefront_id={storefront.id}"


def _split_variant_tokens(value: str | None) -> list[str]:
    if not value:
        return []
    normalized = (
        value.replace("|", "/")
        .replace("-", "/")
        .replace(",", "/")
    )
    return [part.strip() for part in normalized.split("/") if part.strip()]


def _extract_variant_facets(variants: list[ProductVariant] | None) -> tuple[list[str], list[str]]:
    if not variants:
        return [], []

    known_sizes = {
        "xs", "s", "m", "l", "xl", "xxl", "xxxl",
        "2xl", "3xl", "4xl", "5xl",
    }
    sizes: list[str] = []
    colors: list[str] = []
    seen_sizes: set[str] = set()
    seen_colors: set[str] = set()

    for variant in variants:
        for token in _split_variant_tokens(variant.name):
            compact = token.strip()
            normalized = compact.lower().replace(" ", "")
            if normalized in known_sizes or normalized.isdigit():
                if compact not in seen_sizes:
                    seen_sizes.add(compact)
                    sizes.append(compact)
            else:
                title = compact.title()
                if title not in seen_colors:
                    seen_colors.add(title)
                    colors.append(title)

    return sizes, colors


def _serialize_admin_published_product(published_product: PublishedProduct) -> schemas.PublishedProduct:
    base_price = None
    if published_product.product and published_product.product.price is not None:
        base_price = float(published_product.product.price)

    return schemas.PublishedProduct(
        id=published_product.id,
        storefront_id=published_product.storefront_id,
        product_id=published_product.product_id,
        custom_title=published_product.custom_title,
        custom_description=published_product.custom_description,
        slug=published_product.slug,
        price_override=published_product.price_override,
        compare_at_price=published_product.compare_at_price,
        is_published=published_product.is_published,
        is_featured=published_product.is_featured,
        show_stock=published_product.show_stock,
        sort_order=published_product.sort_order,
        seo_title=published_product.seo_title,
        seo_description=published_product.seo_description,
        base_price=base_price,
        company_id=published_product.company_id,
        created_at=published_product.created_at,
        updated_at=published_product.updated_at,
        is_active=published_product.is_active,
    )


def _serialize_public_product(published_product: PublishedProduct, product: Product) -> schemas.PublicProduct:
    title = (published_product.custom_title or product.name or "").strip()
    description = (published_product.custom_description or product.description or "").strip() or None
    base_price = float(product.price or 0)
    price = float(published_product.price_override if published_product.price_override is not None else base_price)
    image_url = published_product.product.image_url or product.image_url
    gallery = [img.image_url for img in sorted(product.images or [], key=lambda item: item.order)]
    if image_url and image_url not in gallery:
        gallery.insert(0, image_url)
    available_sizes, available_colors = _extract_variant_facets(product.variants or [])
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
        image_url=image_url,
        gallery=gallery,
        price=price,
        base_price=base_price,
        compare_at_price=published_product.compare_at_price,
        is_featured=bool(published_product.is_featured),
        show_stock=bool(published_product.show_stock),
        seo_title=published_product.seo_title or title,
        seo_description=published_product.seo_description or description,
    )


def _normalize_catalog_sort(value: str | None) -> str:
    normalized = (value or "latest").strip().lower()
    allowed = {"latest", "best-selling", "price-low", "price-high", "oldest"}
    return normalized if normalized in allowed else "latest"


def _normalize_product_type_label(value: str | None) -> str:
    if not value:
        return "Otro"
    return " ".join(part.capitalize() for part in str(value).lower().split("_"))


def _parse_multi_query_param(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


async def _get_public_storefront_by_id(db: AsyncSession, storefront_id: uuid.UUID) -> Storefront:
    result = await db.execute(
        select(Storefront).where(
            Storefront.id == storefront_id,
            Storefront.is_active == True,
            Storefront.is_enabled == True,
        )
    )
    storefront = result.scalars().first()
    if not storefront:
        raise HTTPException(status_code=404, detail="Storefront not found")
    return storefront


async def _get_public_storefront_by_subdomain(db: AsyncSession, subdomain: str) -> Storefront:
    result = await db.execute(
        select(Storefront).where(
            Storefront.subdomain == subdomain,
            Storefront.is_active == True,
            Storefront.is_enabled == True,
        )
    )
    storefront = result.scalars().first()
    if not storefront:
        raise HTTPException(status_code=404, detail="Storefront not found")
    return storefront


async def _get_public_storefront_by_domain(db: AsyncSession, domain: str) -> Storefront:
    normalized_domain = domain.strip().lower().split(":", 1)[0]
    if not normalized_domain:
        raise HTTPException(status_code=404, detail="Storefront not found")

    result = await db.execute(
        select(Storefront)
        .join(StorefrontDomain, StorefrontDomain.storefront_id == Storefront.id)
        .where(
            StorefrontDomain.domain == normalized_domain,
            StorefrontDomain.is_active == True,
            Storefront.is_active == True,
            Storefront.is_enabled == True,
        )
    )
    storefront = result.scalars().first()
    if not storefront:
        raise HTTPException(status_code=404, detail="Storefront not found")
    return storefront


async def _get_public_collection_or_404(db: AsyncSession, storefront_id: uuid.UUID, slug: str) -> StoreCollection:
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


async def _get_public_published_product_or_404(db: AsyncSession, storefront_id: uuid.UUID, slug: str) -> PublishedProduct:
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
    return gateway


def _gateway_checkout_flow(provider: str, extra_config: dict | None = None) -> str:
    config = extra_config or {}
    if provider in {"manual_transfer", "cod"}:
        return "manual"
    if provider == "wompi":
        return "form_redirect"
    if provider in {"addi", "payu", "paypal"} and config.get("checkout_url"):
        return "redirect"
    return "manual"


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


async def _resolve_default_user_for_company(db: AsyncSession, company_id: uuid.UUID) -> User:
    result = await db.execute(
        select(User).where(
            User.company_id == company_id,
            User.is_active == True,
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

    merged: dict[uuid.UUID, float] = {}
    for item in items:
        if item.quantity <= 0:
            raise HTTPException(status_code=400, detail="Item quantity must be greater than zero")
        merged[item.published_product_id] = merged.get(item.published_product_id, 0.0) + float(item.quantity)

    published_ids = list(merged.keys())
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

    rows: list[schemas.PublicCheckoutPreviewItem] = []
    subtotal = 0.0
    for published_id in published_ids:
        published = published_map[published_id]
        product = published.product
        if not product:
            raise HTTPException(status_code=400, detail="One or more products are not available")
        unit_price = _safe_float(published.price_override, _safe_float(product.price))
        quantity = merged[published_id]
        line_subtotal = unit_price * quantity
        subtotal += line_subtotal
        rows.append(
            schemas.PublicCheckoutPreviewItem(
                published_product_id=published.id,
                product_id=product.id,
                slug=published.slug,
                title=(published.custom_title or product.name or "").strip(),
                quantity=quantity,
                unit_price=unit_price,
                line_subtotal=line_subtotal,
            )
        )

    return rows, subtotal


async def _validate_checkout_inventory(
    db: AsyncSession,
    branch_id: uuid.UUID,
    rows: list[schemas.PublicCheckoutPreviewItem],
) -> None:
    """Prevent a storefront draft from being created for unavailable physical stock."""
    for row in rows:
        product_result = await db.execute(select(Product).where(Product.id == row.product_id))
        product = product_result.scalars().first()
        if not product or not product.track_inventory:
            continue

        inventory_result = await db.execute(
            select(Inventory.quantity).where(
                Inventory.product_id == product.id,
                Inventory.branch_id == branch_id,
            )
        )
        available = _safe_float(inventory_result.scalar_one_or_none())
        if available < row.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente para '{row.title}'. Disponible: {available:g}",
            )


@router.get("/", response_model=List[schemas.Storefront])
async def read_storefronts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    result = await db.execute(
        select(Storefront).where(
            Storefront.company_id == current_user.company_id,
            Storefront.is_active == True,
        )
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
    storefront = Storefront(
        **storefront_in.model_dump(),
        company_id=current_user.company_id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(storefront)
    await db.commit()
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
    for field, value in storefront_in.model_dump(exclude_unset=True).items():
        setattr(storefront, field, value)
    storefront.updated_by_id = current_user.id
    db.add(storefront)
    await db.commit()
    await db.refresh(storefront)
    return storefront


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
    return result.scalars().all()


@router.post("/domains", response_model=schemas.StorefrontDomain)
async def create_storefront_domain(
    *,
    db: AsyncSession = Depends(get_db),
    domain_in: schemas.StorefrontDomainCreate,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    await _get_storefront_or_404(db, domain_in.storefront_id, current_user.company_id)
    domain = StorefrontDomain(
        **domain_in.model_dump(),
        company_id=current_user.company_id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(domain)
    await db.commit()
    await db.refresh(domain)
    return domain


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
    for field, value in domain_in.model_dump(exclude_unset=True).items():
        setattr(domain, field, value)
    domain.updated_by_id = current_user.id
    db.add(domain)
    await db.commit()
    await db.refresh(domain)
    return domain


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
    return result.scalars().all()


@router.post("/payment-gateways", response_model=schemas.StorePaymentGateway)
async def create_payment_gateway(
    *,
    db: AsyncSession = Depends(get_db),
    gateway_in: schemas.StorePaymentGatewayCreate,
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    await _get_storefront_or_404(db, gateway_in.storefront_id, current_user.company_id)
    gateway = StorePaymentGateway(
        **gateway_in.model_dump(),
        company_id=current_user.company_id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(gateway)
    await db.commit()
    await db.refresh(gateway)
    return gateway


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
        setattr(gateway, field, value)
    gateway.updated_by_id = current_user.id
    db.add(gateway)
    await db.commit()
    await db.refresh(gateway)
    return gateway


@router.get("/public/by-subdomain/{subdomain}", response_model=schemas.PublicStorefront)
async def read_public_storefront_by_subdomain(
    subdomain: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    storefront = await _get_public_storefront_by_subdomain(db, subdomain)
    company = await _get_company_for_storefront(db, storefront)
    return schemas.PublicStorefront(
        id=storefront.id,
        name=storefront.name,
        slug=storefront.slug,
        subdomain=storefront.subdomain,
        theme_key=storefront.theme_key,
        theme_settings=storefront.theme_settings or {},
        checkout_settings=storefront.checkout_settings or {},
        seo_settings=storefront.seo_settings or {},
        currency=storefront.currency,
        language=storefront.language,
        branding=_serialize_public_branding(storefront, company),
    )


@router.get("/public/by-domain/{domain}", response_model=schemas.PublicStorefront)
async def read_public_storefront_by_domain(
    domain: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    storefront = await _get_public_storefront_by_domain(db, domain)
    company = await _get_company_for_storefront(db, storefront)
    return schemas.PublicStorefront(
        id=storefront.id,
        name=storefront.name,
        slug=storefront.slug,
        subdomain=storefront.subdomain,
        theme_key=storefront.theme_key,
        theme_settings=storefront.theme_settings or {},
        checkout_settings=storefront.checkout_settings or {},
        seo_settings=storefront.seo_settings or {},
        currency=storefront.currency,
        language=storefront.language,
        branding=_serialize_public_branding(storefront, company),
    )


@router.get("/public/{storefront_id}", response_model=schemas.PublicStorefront)
async def read_public_storefront(
    storefront_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    storefront = await _get_public_storefront_by_id(db, storefront_id)
    company = await _get_company_for_storefront(db, storefront)
    return schemas.PublicStorefront(
        id=storefront.id,
        name=storefront.name,
        slug=storefront.slug,
        subdomain=storefront.subdomain,
        theme_key=storefront.theme_key,
        theme_settings=storefront.theme_settings or {},
        checkout_settings=storefront.checkout_settings or {},
        seo_settings=storefront.seo_settings or {},
        currency=storefront.currency,
        language=storefront.language,
        branding=_serialize_public_branding(storefront, company),
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

    existing = await db.execute(select(User).where(User.email == payload.email))
    existing_user = existing.scalars().first()
    if existing_user:
        raise HTTPException(status_code=400, detail="The email is already registered")

    user = User(
        email=payload.email.strip().lower(),
        hashed_password=security.get_password_hash(payload.password),
        full_name=payload.full_name.strip(),
        company_id=storefront.company_id,
        role_id=None,
        is_superuser=False,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return schemas.PublicStorefrontAuthResponse(
        access_token=_create_storefront_access_token(user, storefront),
        token_type="bearer",
        user=_serialize_public_account_user(user),
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

    result = await db.execute(select(User).where(User.email == payload.email.strip().lower()))
    user = result.scalars().first()
    if not user or not security.verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not _is_storefront_customer(user, storefront):
        raise HTTPException(status_code=403, detail="Storefront account access denied")

    return schemas.PublicStorefrontAuthResponse(
        access_token=_create_storefront_access_token(user, storefront),
        token_type="bearer",
        user=_serialize_public_account_user(user),
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
    result = await db.execute(select(User).where(User.email == payload.email.strip().lower()))
    user = result.scalars().first()

    if user and _is_storefront_customer(user, storefront):
        reset_token = auth.create_access_token(
            data={
                "sub": user.email,
                "type": "storefront_reset",
                "storefront_id": str(storefront.id),
                "scope": "storefront",
            },
            expires_delta=timedelta(hours=1),
        )
        await EmailService.send_storefront_reset_password_email(
            email_to=user.email,
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
        email = token_payload.get("sub")
        token_type = token_payload.get("type")
        token_storefront_id = token_payload.get("storefront_id")
        scope = token_payload.get("scope")
        if (
            not email
            or token_type != "storefront_reset"
            or scope != "storefront"
            or token_storefront_id != str(storefront.id)
        ):
            raise HTTPException(status_code=400, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user or not _is_storefront_customer(user, storefront):
        raise HTTPException(status_code=404, detail="Storefront account not found")

    user.hashed_password = security.get_password_hash(payload.new_password)
    db.add(user)
    await db.commit()
    return schemas.Msg(msg="Password updated successfully")


@router.get("/public/{storefront_id}/account/me", response_model=schemas.PublicStorefrontAccountUser)
async def read_public_storefront_account_me(
    storefront_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    _, user = await _get_current_storefront_customer(storefront_id, db, current_user)
    return _serialize_public_account_user(user)


@router.put("/public/{storefront_id}/account/profile", response_model=schemas.PublicStorefrontAccountUser)
async def update_public_storefront_account_profile(
    storefront_id: uuid.UUID,
    payload: schemas.PublicStorefrontAccountProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    _, user = await _get_current_storefront_customer(storefront_id, db, current_user)
    user.full_name = payload.full_name.strip()
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return _serialize_public_account_user(user)


@router.put("/public/{storefront_id}/account/password", response_model=schemas.Msg)
@limiter.limit("5/minute")
async def change_public_storefront_account_password(
    request: Request,
    storefront_id: uuid.UUID,
    payload: schemas.PublicStorefrontAccountPasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    _, user = await _get_current_storefront_customer(storefront_id, db, current_user)
    if not security.verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="New password must be different")

    user.hashed_password = security.get_password_hash(payload.new_password)
    db.add(user)
    await db.commit()
    return schemas.Msg(msg="Password updated successfully")


@router.get("/public/{storefront_id}/account/orders", response_model=List[schemas.PublicStorefrontAccountOrder])
async def read_public_storefront_account_orders(
    storefront_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    storefront, user = await _get_current_storefront_customer(storefront_id, db, current_user)
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
                StorefrontOrder.customer_user_id == user.id,
                StorefrontOrder.customer_email == user.email.lower(),
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
            )
        )

    legacy_result = await db.execute(
        select(Sale)
        .options(selectinload(Sale.items).selectinload(SaleItem.product))
        .where(
            Sale.company_id == storefront.company_id,
            Sale.notes.ilike(f"%storefront_id={storefront.id}%"),
            Sale.notes.ilike(f"%<{user.email}>%"),
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


@router.get("/public/{storefront_id}/navigation", response_model=List[schemas.PublicStoreNavigationItem])
async def read_public_navigation(
    storefront_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    await _get_public_storefront_by_id(db, storefront_id)
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
) -> Any:
    await _get_public_storefront_by_id(db, storefront_id)
    result = await db.execute(
        select(StorePaymentGateway).where(
            StorePaymentGateway.storefront_id == storefront_id,
            StorePaymentGateway.is_active == True,
            StorePaymentGateway.is_enabled == True,
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
            },
        )
        for gateway in gateways
    ]


@router.get("/public/{storefront_id}/collections", response_model=List[schemas.PublicCollection])
async def read_public_collections(
    storefront_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    await _get_public_storefront_by_id(db, storefront_id)
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
) -> Any:
    collection = await _get_public_collection_or_404(db, storefront_id, slug)
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
    products: list[schemas.PublicProduct] = []
    for link in result.scalars().all():
        published_product = link.published_product
        if not published_product or not published_product.is_published or not published_product.product:
            continue
        products.append(_serialize_public_product(published_product, published_product.product))
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


@router.get("/public/{storefront_id}/products", response_model=schemas.PublicCatalogResponse)
async def read_public_products(
    storefront_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    collection: str | None = None,
    q: str | None = None,
    type: str | None = None,
    size: str | None = None,
    color: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    sort: str = "latest",
    page: int = 1,
    page_size: int = 12,
) -> Any:
    await _get_public_storefront_by_id(db, storefront_id)

    selected_collections = _parse_multi_query_param(collection)
    selected_types = [item.upper() for item in _parse_multi_query_param(type)]
    selected_sizes = [item.lower() for item in _parse_multi_query_param(size)]
    selected_colors = [item.lower() for item in _parse_multi_query_param(color)]
    normalized_search = (q or "").strip().lower()
    normalized_sort = _normalize_catalog_sort(sort)
    current_page = max(1, page)
    safe_page_size = max(1, min(page_size, 48))

    collections_result = await db.execute(
        select(StoreCollection).where(
            StoreCollection.storefront_id == storefront_id,
            StoreCollection.is_active == True,
            StoreCollection.is_visible == True,
        ).order_by(StoreCollection.sort_order.asc(), StoreCollection.name.asc())
    )
    collections = collections_result.scalars().all()
    collection_name_map = {item.slug: item.name for item in collections}

    published_result = await db.execute(
        select(PublishedProduct)
        .options(
            selectinload(PublishedProduct.product).selectinload(Product.images),
            selectinload(PublishedProduct.product).selectinload(Product.category),
            selectinload(PublishedProduct.product).selectinload(Product.brand),
            selectinload(PublishedProduct.product).selectinload(Product.variants),
            selectinload(PublishedProduct.collections)
            .selectinload(StoreCollectionProduct.collection),
        )
        .join(Product, PublishedProduct.product_id == Product.id)
        .where(
            PublishedProduct.storefront_id == storefront_id,
            PublishedProduct.is_active == True,
            PublishedProduct.is_published == True,
            Product.is_active == True,
        )
    )
    published_products = published_result.scalars().unique().all()

    product_collection_map: dict[uuid.UUID, list[str]] = {}
    for published_product in published_products:
        slugs: list[str] = []
        for link in published_product.collections or []:
            collection_model = getattr(link, "collection", None)
            if (
                not collection_model
                or not collection_model.is_active
                or not collection_model.is_visible
                or collection_model.slug in slugs
            ):
                continue
            slugs.append(collection_model.slug)
        product_collection_map[published_product.id] = slugs

    def matches_filters(
        published_product: PublishedProduct,
        *,
        ignore_collection: bool = False,
        ignore_type: bool = False,
        ignore_size: bool = False,
        ignore_color: bool = False,
    ) -> bool:
        product = published_product.product
        if not product:
            return False
        product_collections = product_collection_map.get(published_product.id, [])
        sizes_list, colors_list = _extract_variant_facets(product.variants or [])
        matches_search = (
            not normalized_search
            or normalized_search in (published_product.custom_title or product.name or "").lower()
            or normalized_search in (published_product.slug or "").lower()
            or normalized_search in (product.description or "").lower()
            or normalized_search in ((product.brand.name if getattr(product, "brand", None) else "") or "").lower()
        )
        matches_collection = (
            ignore_collection
            or not selected_collections
            or any(slug in product_collections for slug in selected_collections)
        )
        matches_type = (
            ignore_type
            or not selected_types
            or (product.product_type or "").upper() in selected_types
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
        unit_price = float(
            published_product.price_override
            if published_product.price_override is not None
            else product.price or 0
        )
        matches_min = min_price is None or unit_price >= float(min_price)
        matches_max = max_price is None or unit_price <= float(max_price)
        return (
            matches_search
            and matches_collection
            and matches_type
            and matches_size
            and matches_color
            and matches_min
            and matches_max
        )

    filtered_products = [item for item in published_products if matches_filters(item)]

    def product_sort_key(item: PublishedProduct) -> Any:
        product = item.product
        unit_price = float(
            item.price_override if item.price_override is not None else (product.price if product else 0) or 0
        )
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

    category_counts: dict[str, int] = {item.slug: 0 for item in collections}
    type_counts: dict[str, int] = {}
    size_counts: dict[str, int] = {}
    color_counts: dict[str, int] = {}

    for published_product in published_products:
        product = published_product.product
        if not product:
            continue
        if matches_filters(published_product, ignore_collection=True):
            for slug_value in product_collection_map.get(published_product.id, []):
                if slug_value in category_counts:
                    category_counts[slug_value] += 1
        if matches_filters(published_product, ignore_type=True):
            product_type_value = (product.product_type or "OTHER").upper()
            type_counts[product_type_value] = type_counts.get(product_type_value, 0) + 1
        sizes_list, colors_list = _extract_variant_facets(product.variants or [])
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
            _serialize_public_product(published_product, published_product.product)
            for published_product in paginated_products
            if published_product.product
        ],
        categories=[
            schemas.PublicCatalogCategory(
                name=item.name,
                slug=item.slug,
                products=category_counts.get(item.slug, 0),
                is_refined=item.slug in selected_collections,
            )
            for item in collections
        ],
        product_types=[
            schemas.PublicCatalogProductType(
                name=_normalize_product_type_label(value),
                value=value,
                products=count,
                is_refined=value in selected_types,
            )
            for value, count in sorted(type_counts.items(), key=lambda entry: entry[0])
        ],
        sizes=[
            schemas.PublicCatalogFacet(
                value=value,
                products=count,
                is_refined=value.lower() in selected_sizes,
            )
            for value, count in sorted(size_counts.items(), key=lambda entry: entry[0])
        ],
        colors=[
            schemas.PublicCatalogFacet(
                value=value,
                products=count,
                is_refined=value.lower() in selected_colors,
            )
            for value, count in sorted(color_counts.items(), key=lambda entry: entry[0])
        ],
        total_products=total_products,
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
) -> Any:
    await _get_public_storefront_by_id(db, storefront_id)
    published_product = await _get_public_published_product_or_404(db, storefront_id, slug)
    return _serialize_public_product(published_product, published_product.product)


@router.post("/public/{storefront_id}/checkout/preview", response_model=schemas.PublicCheckoutPreviewResponse)
async def preview_public_checkout(
    storefront_id: uuid.UUID,
    payload: schemas.PublicCheckoutPreviewRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    storefront = await _get_public_storefront_by_id(db, storefront_id)
    rows, subtotal = await _load_checkout_products(db, storefront_id, payload.items)

    discount = max(0.0, _safe_float(payload.discount_amount))
    shipping = max(0.0, _safe_float(payload.shipping_amount))
    tax = 0.0
    total = max(0.0, subtotal - discount + shipping + tax)

    return schemas.PublicCheckoutPreviewResponse(
        currency=storefront.currency,
        items=rows,
        subtotal=subtotal,
        discount=discount,
        shipping=shipping,
        tax=tax,
        total=total,
    )


@router.post("/public/{storefront_id}/checkout/orders", response_model=schemas.PublicCheckoutCreateOrderResponse)
async def create_public_checkout_order(
    storefront_id: uuid.UUID,
    payload: schemas.PublicCheckoutCreateOrderRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    storefront = await _get_public_storefront_by_id(db, storefront_id)
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
    rows, subtotal = await _load_checkout_products(db, storefront_id, payload.items)

    discount = max(0.0, _safe_float(payload.discount_amount))
    shipping = max(0.0, _safe_float(payload.shipping_amount))
    tax = 0.0
    total = max(0.0, subtotal - discount + shipping + tax)

    branch = await _resolve_default_branch_for_company(db, storefront.company_id)
    await _validate_checkout_inventory(db, branch.id, rows)
    sale_user = await _resolve_default_user_for_company(db, storefront.company_id)
    storefront_customer_user = await _get_storefront_customer_user_by_email(db, storefront, payload.customer.email)
    storefront_client = await _get_or_create_storefront_client(db, storefront, payload)

    notes_parts = [
        "Ecommerce order",
        f"storefront_id={storefront.id}",
        f"customer={customer_name}<{customer_email}>",
        f"phone={payload.customer.phone or ''}",
        f"document_id={payload.customer.document_id or ''}",
        f"address={address_line1}",
        f"city={payload.address.city or ''}",
        f"state={payload.address.state or ''}",
        f"country={payload.address.country or ''}",
        f"postal_code={payload.address.postal_code or ''}",
        f"provider={gateway.provider}",
    ]
    if payload.coupon_code:
        notes_parts.append(f"coupon={payload.coupon_code}")
    if payload.notes:
        notes_parts.append(f"buyer_note={payload.notes}")

    sale = Sale(
        branch_id=branch.id,
        user_id=sale_user.id,
        client_id=storefront_client.id if storefront_client else None,
        status=SaleStatus.DRAFT,
        payment_method=gateway.provider,
        notes=" | ".join(notes_parts),
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
    db.add(sale)
    await db.flush()

    for row in rows:
        db.add(
            SaleItem(
                sale_id=sale.id,
                product_id=row.product_id,
                quantity=row.quantity,
                quantity_picked=0.0,
                price=row.unit_price,
                discount=0.0,
                total=row.line_subtotal,
                company_id=storefront.company_id,
            created_by_id=sale_user.id,
            updated_by_id=sale_user.id,
        )
    )

    db.add(
        StorefrontOrder(
            storefront_id=storefront.id,
            sale_id=sale.id,
            idempotency_key=idempotency_key,
            customer_user_id=storefront_customer_user.id if storefront_customer_user else None,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=payload.customer.phone,
            customer_document_id=payload.customer.document_id,
            shipping_line1=address_line1,
            shipping_city=_normalize_checkout_text(payload.address.city),
            shipping_state=_normalize_checkout_text(payload.address.state),
            shipping_country=_normalize_checkout_text(payload.address.country),
            shipping_postal_code=_normalize_checkout_text(payload.address.postal_code),
            coupon_code=payload.coupon_code,
            buyer_note=payload.notes,
            payment_provider=gateway.provider,
            payment_status="pending",
            currency=storefront.currency,
            company_id=storefront.company_id,
            created_by_id=sale_user.id,
            updated_by_id=sale_user.id,
        )
    )

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

    await db.commit()
    await db.refresh(sale)
    return _build_checkout_order_response(
        storefront=storefront,
        sale=sale,
        payment_provider=gateway.provider,
        payment_status="pending",
    )


@router.post("/public/{storefront_id}/checkout/payment-intent", response_model=schemas.PublicPaymentIntentResponse)
async def create_public_payment_intent(
    storefront_id: uuid.UUID,
    payload: schemas.PublicPaymentIntentRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    storefront = await _get_public_storefront_by_id(db, storefront_id)
    gateway = await _get_enabled_gateway_for_storefront(db, storefront_id, payload.provider)

    amount = max(0.0, _safe_float(payload.amount))
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")

    mode = "sandbox" if gateway.is_sandbox else "production"
    external_reference = str(payload.order_id) if payload.order_id else f"{storefront.slug}-{uuid.uuid4().hex[:10]}"
    metadata = {
        "storefront_id": str(storefront.id),
        "order_id": str(payload.order_id) if payload.order_id else None,
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
    elif gateway.provider == "wompi":
        currency = (payload.currency or storefront.currency or "COP").upper()
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
        checkout_url = extra_config.get("checkout_url") or "https://checkout.payulatam.com/ppp-web-gateway-payu/"
        provider_payload = {"method": "GET", "action": checkout_url, "fields": {}}
    elif gateway.provider == "paypal":
        checkout_url = extra_config.get("checkout_url") or "https://www.paypal.com/checkoutnow"
        provider_payload = {"method": "GET", "action": checkout_url, "fields": {}}
    elif gateway.provider == "addi":
        checkout_url = extra_config.get("checkout_url")
        instructions = (
            extra_config.get("instructions")
            or "Configura la URL oficial de checkout de Addi para redirigir al cliente."
        )
        if checkout_url:
            provider_payload = {"method": "GET", "action": checkout_url, "fields": {}}

    return schemas.PublicPaymentIntentResponse(
        provider=gateway.provider,
        flow=flow,
        mode=mode,
        amount=amount,
        currency=payload.currency or storefront.currency,
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
                .options(selectinload(StorefrontOrder.sale))
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

    if storefront_order:
        storefront_order.payment_status = status.lower()
        storefront_order.updated_by_id = storefront_order.updated_by_id or storefront_order.created_by_id
        db.add(storefront_order)

    if sale:
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
            sale.status = SaleStatus.CONFIRMED
        elif status in {"DECLINED", "ERROR", "VOIDED"}:
            sale.status = SaleStatus.CANCELLED
        sale.updated_by_id = sale.updated_by_id or sale.created_by_id
        db.add(sale)
        await db.commit()

    return schemas.PublicPaymentStatusResponse(
        provider=clean_provider,
        transaction_id=clean_transaction_id,
        external_reference=str(external_reference) if external_reference else None,
        status=status,
        status_message=status_message or f"Estado consultado en Wompi ({mode})",
        order_id=sale.id if sale else None,
        order_code=str(sale.id).split("-")[0].upper() if sale else None,
    )
