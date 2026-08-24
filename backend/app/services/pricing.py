"""Shared price-list resolution for catalog, checkout and POS."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import IntegrationProductPrice
from app.models.integration import IntegrationRecordLink
from app.models.pricelist import PriceList
from app.models.pricelist_item import PriceListItem
from app.models.pricelist_source_rule import PriceListSourceRule
from app.models.product import Product
from app.models.product_variant import ProductVariant


@dataclass
class ProductPricing:
    base_price: float
    variant_prices: dict[uuid.UUID, float] = field(default_factory=dict)


@dataclass
class PriceListContext:
    price_list: PriceList | None = None
    items: dict[tuple[uuid.UUID, uuid.UUID | None], float | None] = field(default_factory=dict)
    external: dict[tuple[uuid.UUID, uuid.UUID | None], tuple[float | None, float | None]] = field(default_factory=dict)
    external_by_source: dict[uuid.UUID, dict[tuple[uuid.UUID, uuid.UUID | None], tuple[float | None, float | None]]] = field(default_factory=dict)
    source_rules: list[PriceListSourceRule] = field(default_factory=list)
    product_sources: dict[uuid.UUID, set[uuid.UUID]] = field(default_factory=dict)
    variant_sources: dict[uuid.UUID, set[uuid.UUID]] = field(default_factory=dict)


async def load_price_list_context(
    db: AsyncSession,
    price_list_id: uuid.UUID | None,
    product_ids: list[uuid.UUID],
    company_id: uuid.UUID | None = None,
) -> PriceListContext:
    """Load one list and all values for a product page in bounded queries."""
    if not price_list_id or not product_ids:
        return PriceListContext()

    price_list_filters = [
            PriceList.id == price_list_id,
            PriceList.is_active.is_(True),
            PriceList.active.is_(True),
            PriceList.type == "SALE",
        ]
    if company_id is not None:
        price_list_filters.append(PriceList.company_id == company_id)
    price_list = await db.scalar(select(PriceList).where(*price_list_filters))
    if not price_list:
        return PriceListContext()

    item_result = await db.execute(
        select(PriceListItem).where(
            PriceListItem.pricelist_id == price_list.id,
            PriceListItem.product_id.in_(product_ids),
            PriceListItem.is_active.is_(True),
        )
    )
    items = {
        (item.product_id, item.variant_id): item.price
        for item in item_result.scalars().all()
    }

    rule_result = await db.execute(
        select(PriceListSourceRule)
        .where(
            PriceListSourceRule.pricelist_id == price_list.id,
            PriceListSourceRule.is_active.is_(True),
        )
        .order_by(PriceListSourceRule.created_at.asc(), PriceListSourceRule.id.asc())
    )
    source_rules = list(rule_result.scalars().all())
    source_ids = {rule.source_id for rule in source_rules}
    if price_list.source_id:
        source_ids.add(price_list.source_id)

    link_result = await db.execute(
        select(
            IntegrationRecordLink.source_id,
            IntegrationRecordLink.local_product_id,
            IntegrationRecordLink.local_variant_id,
        ).where(
            IntegrationRecordLink.source_id.in_(source_ids) if source_ids else False,
            IntegrationRecordLink.local_product_id.in_(product_ids),
            IntegrationRecordLink.is_active.is_(True),
        )
    )
    product_sources: dict[uuid.UUID, set[uuid.UUID]] = {}
    variant_sources: dict[uuid.UUID, set[uuid.UUID]] = {}
    for source_id, product_id, variant_id in link_result.all():
        if product_id:
            product_sources.setdefault(product_id, set()).add(source_id)
        if variant_id:
            variant_sources.setdefault(variant_id, set()).add(source_id)

    external_by_source: dict[uuid.UUID, dict[tuple[uuid.UUID, uuid.UUID | None], tuple[float | None, float | None]]] = {}
    if source_ids:
        external_result = await db.execute(
            select(IntegrationProductPrice).where(
                IntegrationProductPrice.source_id.in_(source_ids),
                IntegrationProductPrice.product_id.in_(product_ids),
                IntegrationProductPrice.is_active.is_(True),
            )
        )
        for row in external_result.scalars().all():
            external_by_source.setdefault(row.source_id, {})[(row.product_id, row.variant_id)] = (
                row.external_price,
                row.external_cost,
            )

    external = external_by_source.get(price_list.source_id, {}) if price_list.source_id else {}

    return PriceListContext(
        price_list=price_list,
        items=items,
        external=external,
        external_by_source=external_by_source,
        source_rules=source_rules,
        product_sources=product_sources,
        variant_sources=variant_sources,
    )


def _internal_price(product: Product, variant: ProductVariant | None) -> float:
    if variant is not None and variant.price is not None:
        return float(variant.price)
    if variant is not None:
        return float(product.price or 0) + float(variant.price_extra or 0)
    return float(product.price or 0)


def _internal_cost(product: Product, variant: ProductVariant | None) -> float:
    if variant is not None and variant.cost is not None:
        return float(variant.cost)
    if variant is not None:
        return float(product.cost or 0) + float(variant.cost_extra or 0)
    return float(product.cost or 0)


def _external_values_for_source(
    context: PriceListContext,
    source_id: uuid.UUID,
    product: Product,
    variant: ProductVariant | None,
) -> tuple[float | None, float | None] | None:
    values = context.external_by_source.get(source_id, {})
    key = (product.id, variant.id if variant else None)
    product_key = (product.id, None)
    if key in values:
        return values[key]
    if product_key in values:
        return values[product_key]
    return None


def _rule_for_product(
    context: PriceListContext,
    product: Product,
    variant: ProductVariant | None,
) -> tuple[PriceList | PriceListSourceRule | None, tuple[float | None, float | None] | None]:
    if not context.price_list:
        return None, None
    memberships = set(context.product_sources.get(product.id, set()))
    if variant is not None:
        memberships.update(context.variant_sources.get(variant.id, set()))
    membership_rule: PriceListSourceRule | None = None
    for rule in context.source_rules:
        values = _external_values_for_source(context, rule.source_id, product, variant)
        if values is not None:
            return rule, values
        if membership_rule is None and rule.source_id in memberships:
            membership_rule = rule
    if membership_rule is not None:
        return membership_rule, None
    if context.price_list.source_id:
        return context.price_list, _external_values_for_source(context, context.price_list.source_id, product, variant)
    return context.price_list, None


def _base_value(
    context: PriceListContext,
    product: Product,
    variant: ProductVariant | None,
    rule: PriceList | PriceListSourceRule | None,
    external_values: tuple[float | None, float | None] | None,
) -> float:
    if not rule:
        return _internal_price(product, variant)
    external_price, external_cost = external_values or (None, None)
    if rule.base_source == "EXTERNAL_PRICE" and external_price is not None:
        return float(external_price)
    if rule.base_source == "EXTERNAL_COST" and external_cost is not None:
        return float(external_cost)
    if rule.base_source == "INTERNAL_COST":
        return _internal_cost(product, variant)
    return _internal_price(product, variant)


def resolve_price(
    context: PriceListContext,
    product: Product,
    variant: ProductVariant | None = None,
) -> float:
    """Return the effective sale price without mutating product data."""
    if not context.price_list:
        return _internal_price(product, variant)

    price_list = context.price_list
    key = (product.id, variant.id if variant else None)
    override = context.items.get(key)
    if override is None and variant is not None:
        override = context.items.get((product.id, None))
    if override is not None:
        value = float(override)
    else:
        rule, external_values = _rule_for_product(context, product, variant)
        if not rule:
            return _internal_price(product, variant)
        base = _base_value(context, product, variant, rule, external_values)
        if rule.pricing_mode == "MARKUP_PERCENT":
            value = base * (1 + float(rule.adjustment_value or 0) / 100)
        elif rule.pricing_mode == "MARKUP_AMOUNT":
            value = base + float(rule.adjustment_value or 0)
        else:
            value = _internal_price(product, variant)

        if rule.min_margin_percent is not None:
            minimum = _internal_cost(product, variant) * (1 + float(rule.min_margin_percent) / 100)
            value = max(value, minimum)

    rule, _external_values = _rule_for_product(context, product, variant)
    step = float((rule.rounding_step if rule else price_list.rounding_step) or 0)
    if step > 0:
        value = float(
            (Decimal(str(value)) / Decimal(str(step))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            * Decimal(str(step))
        )
    return max(0.0, round(value, 2))


def selected_external_values(
    context: PriceListContext,
    product: Product,
    variant: ProductVariant | None = None,
) -> tuple[float | None, float | None]:
    """Return the provider snapshot selected by the list's source rules."""
    _rule, values = _rule_for_product(context, product, variant)
    return values or (None, None)


def resolve_product_pricing(context: PriceListContext, product: Product) -> ProductPricing:
    return ProductPricing(
        base_price=resolve_price(context, product),
        variant_prices={
            variant.id: resolve_price(context, product, variant)
            for variant in (product.variants or [])
        },
    )
