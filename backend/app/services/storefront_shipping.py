"""Tenant-scoped shipping configuration and server-side rate calculation."""

from dataclasses import dataclass
import unicodedata
from typing import Any
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.storefront import (
    Storefront,
    StorefrontShippingMethod,
    StorefrontShippingRule,
)


CHARGE_TYPES = {"free", "flat", "weight", "percentage", "quote"}
DESTINATION_TYPES = {"global", "department", "city"}
METHOD_TYPES = {"delivery", "pickup", "quote"}


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _key(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in normalized if not unicodedata.combining(char)).strip().casefold()


def _text(value: Any) -> str | None:
    result = str(value or "").strip()
    return result or None


@dataclass
class ShippingCalculation:
    shipping: float
    total_weight: float
    method: StorefrontShippingMethod | None = None
    rule: StorefrontShippingRule | None = None
    quote_required: bool = False
    requires_destination: bool = False


def validate_shipping_rule_values(rule: Any) -> None:
    destination_type = str(getattr(rule, "destination_type", "global") or "global").lower()
    charge_type = str(getattr(rule, "charge_type", "flat") or "flat").lower()
    if destination_type not in DESTINATION_TYPES:
        raise HTTPException(status_code=422, detail="El alcance del destino no es válido")
    if charge_type not in CHARGE_TYPES:
        raise HTTPException(status_code=422, detail="El tipo de tarifa no es válido")
    if destination_type == "department" and not (
        _text(getattr(rule, "state_code", None)) or _text(getattr(rule, "state_name", None))
    ):
        raise HTTPException(status_code=422, detail="Una regla por departamento requiere el departamento")
    if destination_type == "city" and not (
        _text(getattr(rule, "city_code", None)) or _text(getattr(rule, "city_name", None))
    ):
        raise HTTPException(status_code=422, detail="Una regla por ciudad requiere la ciudad")
    min_subtotal = getattr(rule, "min_subtotal", None)
    max_subtotal = getattr(rule, "max_subtotal", None)
    min_weight = getattr(rule, "min_weight", None)
    max_weight = getattr(rule, "max_weight", None)
    if min_subtotal is not None and max_subtotal is not None and min_subtotal > max_subtotal:
        raise HTTPException(status_code=422, detail="El subtotal mínimo no puede superar al máximo")
    if min_weight is not None and max_weight is not None and min_weight > max_weight:
        raise HTTPException(status_code=422, detail="El peso mínimo no puede superar al máximo")
    if charge_type == "percentage" and _number(getattr(rule, "amount", 0)) > 100:
        raise HTTPException(status_code=422, detail="El porcentaje de envío no puede superar 100")


async def ensure_default_shipping_configuration(
    db: AsyncSession,
    storefront: Storefront,
    user_id: uuid.UUID | None = None,
) -> bool:
    """Create a compatibility method for stores created before shipping rules."""
    existing = await db.scalar(
        select(StorefrontShippingMethod.id).where(
            StorefrontShippingMethod.storefront_id == storefront.id,
            StorefrontShippingMethod.is_active == True,
        ).limit(1)
    )
    if existing:
        return False

    settings = storefront.checkout_settings or {}
    method = StorefrontShippingMethod(
        storefront_id=storefront.id,
        company_id=storefront.company_id,
        code="standard",
        name="Entrega estándar",
        description="Envío estándar configurado por la tienda.",
        method_type="delivery",
        is_enabled=True,
        sort_order=0,
        created_by_id=user_id,
        updated_by_id=user_id,
    )
    db.add(method)
    await db.flush()

    threshold = max(0.0, _number(settings.get("free_shipping_threshold")))
    flat_rate = max(0.0, _number(settings.get("flat_shipping_rate")))
    if threshold > 0:
        db.add(StorefrontShippingRule(
            storefront_id=storefront.id,
            method_id=method.id,
            company_id=storefront.company_id,
            name=f"Envío gratis desde {threshold:g}",
            priority=10,
            destination_type="global",
            country_code="CO",
            min_subtotal=threshold,
            charge_type="free",
            amount=0,
            rate_per_kg=0,
            created_by_id=user_id,
            updated_by_id=user_id,
        ))
    db.add(StorefrontShippingRule(
        storefront_id=storefront.id,
        method_id=method.id,
        company_id=storefront.company_id,
        name="Tarifa base",
        priority=100,
        destination_type="global",
        country_code="CO",
        charge_type="flat",
        amount=flat_rate,
        rate_per_kg=0,
        created_by_id=user_id,
        updated_by_id=user_id,
    ))
    await db.flush()
    return True


async def calculate_shipping(
    db: AsyncSession,
    storefront: Storefront,
    rows: list[Any],
    subtotal: float,
    address: Any = None,
    payment_provider: str | None = None,
    method_id: uuid.UUID | None = None,
    allow_missing_destination: bool = True,
) -> ShippingCalculation:
    """Resolve the first matching rule. Client-provided amounts are never used."""
    methods_result = await db.execute(
        select(StorefrontShippingMethod).where(
            StorefrontShippingMethod.storefront_id == storefront.id,
            StorefrontShippingMethod.is_active == True,
            StorefrontShippingMethod.is_enabled == True,
        ).order_by(StorefrontShippingMethod.sort_order.asc(), StorefrontShippingMethod.created_at.asc())
    )
    methods = methods_result.scalars().all()
    total_weight = 0.0
    product_ids = [row.product_id for row in rows]
    if product_ids:
        products_result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
        products = {product.id: product for product in products_result.scalars().all()}
        total_weight = sum(max(0.0, _number(products.get(row.product_id).weight if products.get(row.product_id) else 0)) * row.quantity for row in rows)

    if not methods:
        settings = storefront.checkout_settings or {}
        threshold = max(0.0, _number(settings.get("free_shipping_threshold")))
        flat_rate = max(0.0, _number(settings.get("flat_shipping_rate")))
        return ShippingCalculation(
            shipping=0.0 if threshold and subtotal >= threshold else flat_rate,
            total_weight=total_weight,
        )

    method = next((item for item in methods if method_id and item.id == method_id), None) or methods[0]
    if method_id and not any(item.id == method_id for item in methods):
        raise HTTPException(status_code=400, detail="El método de envío seleccionado no está disponible")

    address_country = _key(getattr(address, "country", None) or "CO")
    address_state = _key(getattr(address, "state", None))
    address_state_code = _key(getattr(address, "state_code", None))
    address_city = _key(getattr(address, "city", None))
    address_city_code = _key(getattr(address, "city_code", None))
    provider = _key(payment_provider)
    rules_result = await db.execute(
        select(StorefrontShippingRule).where(
            StorefrontShippingRule.storefront_id == storefront.id,
            StorefrontShippingRule.method_id == method.id,
            StorefrontShippingRule.is_active == True,
            StorefrontShippingRule.is_enabled == True,
        ).order_by(StorefrontShippingRule.priority.asc(), StorefrontShippingRule.created_at.asc())
    )
    rules = rules_result.scalars().all()
    destination_missing = not (address_state or address_state_code or address_city or address_city_code)

    for rule in rules:
        country = _key(rule.country_code)
        if country and country != address_country:
            continue
        rule_provider = _key(rule.payment_provider)
        if rule_provider and rule_provider not in {"any", provider}:
            continue
        if rule.min_subtotal is not None and subtotal < rule.min_subtotal:
            continue
        if rule.max_subtotal is not None and subtotal > rule.max_subtotal:
            continue
        if rule.min_weight is not None and total_weight < rule.min_weight:
            continue
        if rule.max_weight is not None and total_weight > rule.max_weight:
            continue

        destination_type = (rule.destination_type or "global").lower()
        if destination_type == "department":
            if not (address_state == _key(rule.state_name) or address_state_code == _key(rule.state_code)):
                continue
        elif destination_type == "city":
            if not (address_city == _key(rule.city_name) or address_city_code == _key(rule.city_code)):
                continue
            if rule.state_code or rule.state_name:
                if not (address_state == _key(rule.state_name) or address_state_code == _key(rule.state_code)):
                    continue
        elif destination_type != "global":
            continue

        if destination_missing and destination_type != "global":
            continue
        charge_type = (rule.charge_type or "flat").lower()
        if charge_type == "free":
            amount = 0.0
        elif charge_type == "weight":
            amount = _number(rule.amount) + (_number(rule.rate_per_kg) * total_weight)
        elif charge_type == "percentage":
            amount = subtotal * _number(rule.amount) / 100
        elif charge_type == "quote":
            amount = 0.0
        else:
            amount = _number(rule.amount)
        return ShippingCalculation(
            shipping=round(max(0.0, amount), 2),
            total_weight=round(total_weight, 3),
            method=method,
            rule=rule,
            quote_required=charge_type == "quote" or method.method_type == "quote",
        )

    if destination_missing and allow_missing_destination:
        return ShippingCalculation(
            shipping=0.0,
            total_weight=round(total_weight, 3),
            method=method,
            requires_destination=True,
        )
    raise HTTPException(status_code=400, detail="No hay una tarifa de envío disponible para ese destino y método")
