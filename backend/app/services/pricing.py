"""Shared price-list resolution for catalog, checkout and POS."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import IntegrationProductPrice
from app.models.pricelist import PriceList
from app.models.pricelist_item import PriceListItem
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

    external: dict[tuple[uuid.UUID, uuid.UUID | None], tuple[float | None, float | None]] = {}
    if price_list.source_id:
        external_result = await db.execute(
            select(IntegrationProductPrice).where(
                IntegrationProductPrice.source_id == price_list.source_id,
                IntegrationProductPrice.product_id.in_(product_ids),
                IntegrationProductPrice.is_active.is_(True),
            )
        )
        external = {
            (row.product_id, row.variant_id): (row.external_price, row.external_cost)
            for row in external_result.scalars().all()
        }

    return PriceListContext(price_list=price_list, items=items, external=external)


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


def _external_values(
    context: PriceListContext,
    product: Product,
    variant: ProductVariant | None,
) -> tuple[float | None, float | None]:
    key = (product.id, variant.id if variant else None)
    product_key = (product.id, None)
    return context.external.get(key) or context.external.get(product_key) or (None, None)


def _base_value(
    context: PriceListContext,
    product: Product,
    variant: ProductVariant | None,
) -> float:
    price_list = context.price_list
    if not price_list:
        return _internal_price(product, variant)
    external_price, external_cost = _external_values(context, product, variant)
    if price_list.base_source == "EXTERNAL_PRICE" and external_price is not None:
        return float(external_price)
    if price_list.base_source == "EXTERNAL_COST" and external_cost is not None:
        return float(external_cost)
    if price_list.base_source == "INTERNAL_COST":
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
        base = _base_value(context, product, variant)
        if price_list.pricing_mode == "MARKUP_PERCENT":
            value = base * (1 + float(price_list.adjustment_value or 0) / 100)
        elif price_list.pricing_mode == "MARKUP_AMOUNT":
            value = base + float(price_list.adjustment_value or 0)
        else:
            value = _internal_price(product, variant)

        if price_list.min_margin_percent is not None:
            minimum = _internal_cost(product, variant) * (1 + float(price_list.min_margin_percent) / 100)
            value = max(value, minimum)

    step = float(price_list.rounding_step or 0)
    if step > 0:
        value = float(
            (Decimal(str(value)) / Decimal(str(step))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            * Decimal(str(step))
        )
    return max(0.0, round(value, 2))


def resolve_product_pricing(context: PriceListContext, product: Product) -> ProductPricing:
    return ProductPricing(
        base_price=resolve_price(context, product),
        variant_prices={
            variant.id: resolve_price(context, product, variant)
            for variant in (product.variants or [])
        },
    )
