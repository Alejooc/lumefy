"""Rule evaluation and synchronization for automated storefront collections."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inventory import Inventory
from app.models.product import Product
from app.models.storefront import PublishedProduct, StoreCollection, StoreCollectionProduct


COLLECTION_RULE_FIELDS = {
    "title",
    "description",
    "vendor",
    "brand",
    "product_type",
    "category",
    "tag",
    "sku",
    "price",
    "inventory",
    "status",
    "variant_title",
}

COLLECTION_RULE_OPERATORS = {
    "equals",
    "not_equals",
    "contains",
    "not_contains",
    "starts_with",
    "ends_with",
    "greater_than",
    "less_than",
    "greater_or_equal",
    "less_or_equal",
}


def normalize_rule_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text).strip().casefold()


def _flatten_attribute_values(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for nested in value.values():
            yield from _flatten_attribute_values(nested)
    elif isinstance(value, (list, tuple, set)):
        for nested in value:
            yield from _flatten_attribute_values(nested)
    elif value is not None:
        yield str(value)


def _attribute_tags(attributes: Any) -> list[str]:
    if not isinstance(attributes, dict):
        return []
    values: list[str] = []
    for key in ("tag", "tags", "labels", "etiqueta", "etiquetas"):
        if key in attributes:
            values.extend(_flatten_attribute_values(attributes[key]))
    return values


def product_rule_facts(published_product: PublishedProduct, inventory: float = 0) -> dict[str, Any]:
    product = published_product.product
    if product is None:
        return {}

    title = getattr(published_product, "custom_title", None) or product.name
    description = getattr(published_product, "custom_description", None) or product.description
    brand = getattr(getattr(product, "brand", None), "name", None)
    supplier = getattr(getattr(product, "supplier", None), "name", None)
    vendor = " / ".join(value for value in (supplier, brand) if value)
    category = getattr(getattr(product, "category", None), "name", None)
    variant_titles = [variant.name for variant in (product.variants or []) if variant.name]
    variant_skus = [variant.sku for variant in (product.variants or []) if variant.sku]

    return {
        "title": title,
        "description": description,
        "vendor": vendor,
        "brand": brand,
        "product_type": product.product_type,
        "category": category,
        "tag": _attribute_tags(product.attributes),
        "sku": [product.sku, *variant_skus],
        "price": published_product.price_override if published_product.price_override is not None else product.price,
        "inventory": inventory,
        "status": "active" if published_product.is_published and product.is_active else "draft",
        "variant_title": variant_titles,
    }


def rule_matches_product(rule: Any, facts: dict[str, Any]) -> bool:
    field = str(getattr(rule, "field", ""))
    operator = str(getattr(rule, "operator", ""))
    if field not in COLLECTION_RULE_FIELDS or operator not in COLLECTION_RULE_OPERATORS:
        return False

    expected = normalize_rule_text(getattr(rule, "value", ""))
    raw_value = facts.get(field, "")
    values = list(raw_value) if isinstance(raw_value, (list, tuple, set)) else [raw_value]

    if field in {"price", "inventory"}:
        try:
            expected_number = float(str(getattr(rule, "value", "")).replace(",", ".").strip())
        except (TypeError, ValueError):
            return False
        numbers: list[float] = []
        for value in values:
            try:
                numbers.append(float(value))
            except (TypeError, ValueError):
                continue
        if not numbers:
            return False
        if operator == "equals":
            return any(number == expected_number for number in numbers)
        if operator == "not_equals":
            return all(number != expected_number for number in numbers)
        if operator == "greater_than":
            return any(number > expected_number for number in numbers)
        if operator == "less_than":
            return any(number < expected_number for number in numbers)
        if operator == "greater_or_equal":
            return any(number >= expected_number for number in numbers)
        if operator == "less_or_equal":
            return any(number <= expected_number for number in numbers)
        return False

    normalized_values = [normalize_rule_text(value) for value in values]
    if operator == "equals":
        return any(value == expected for value in normalized_values)
    if operator == "not_equals":
        return all(value != expected for value in normalized_values)
    if operator == "contains":
        return any(expected in value for value in normalized_values)
    if operator == "not_contains":
        return all(expected not in value for value in normalized_values)
    if operator == "starts_with":
        return any(value.startswith(expected) for value in normalized_values)
    if operator == "ends_with":
        return any(value.endswith(expected) for value in normalized_values)
    return False


def collection_matches_product(collection: StoreCollection, facts: dict[str, Any]) -> bool:
    rules = [rule for rule in (collection.rules or []) if rule.is_active and rule.value is not None]
    if collection.collection_mode != "automated" or not rules:
        return False
    results = [rule_matches_product(rule, facts) for rule in rules]
    return any(results) if collection.rule_match == "any" else all(results)


async def _load_published_products(
    db: AsyncSession,
    *,
    storefront_id: UUID,
    company_id: UUID,
    product_ids: list[UUID] | None = None,
) -> list[PublishedProduct]:
    query = (
        select(PublishedProduct)
        .options(
            selectinload(PublishedProduct.product).selectinload(Product.category),
            selectinload(PublishedProduct.product).selectinload(Product.brand),
            selectinload(PublishedProduct.product).selectinload(Product.supplier),
            selectinload(PublishedProduct.product).selectinload(Product.variants),
        )
        .where(
            PublishedProduct.storefront_id == storefront_id,
            PublishedProduct.company_id == company_id,
            PublishedProduct.is_active == True,
        )
    )
    if product_ids:
        query = query.where(PublishedProduct.id.in_(product_ids))

    result = await db.execute(query)
    products = list(result.scalars().all())
    if not products:
        return []

    inventory_result = await db.execute(
        select(
            Inventory.product_id,
            func.coalesce(func.sum(Inventory.quantity - Inventory.reserved_quantity), 0),
        )
        .where(
            Inventory.company_id == company_id,
            Inventory.product_id.in_([item.product_id for item in products]),
        )
        .group_by(Inventory.product_id)
    )
    inventory_by_product = {product_id: float(quantity or 0) for product_id, quantity in inventory_result.all()}
    for item in products:
        item._collection_inventory = inventory_by_product.get(item.product_id, 0)  # type: ignore[attr-defined]
    return products


async def _load_automated_collections(
    db: AsyncSession,
    *,
    storefront_id: UUID,
    company_id: UUID,
    collection_id: UUID | None = None,
) -> list[StoreCollection]:
    query = (
        select(StoreCollection)
        .options(selectinload(StoreCollection.rules))
        .where(
            StoreCollection.storefront_id == storefront_id,
            StoreCollection.company_id == company_id,
            StoreCollection.is_active == True,
            StoreCollection.collection_mode == "automated",
        )
    )
    if collection_id:
        query = query.where(StoreCollection.id == collection_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def reconcile_automated_collections(
    db: AsyncSession,
    *,
    storefront_id: UUID,
    company_id: UUID,
    user_id: UUID | None = None,
    product_ids: list[UUID] | None = None,
    collection_id: UUID | None = None,
) -> dict[str, int]:
    """Make active collection links match their automated rules.

    The function intentionally does not commit, so callers can include the
    collection sync in the same transaction as a product publication/update.
    """
    collections = await _load_automated_collections(
        db,
        storefront_id=storefront_id,
        company_id=company_id,
        collection_id=collection_id,
    )
    products = await _load_published_products(
        db,
        storefront_id=storefront_id,
        company_id=company_id,
        product_ids=product_ids,
    )
    if not collections or not products:
        return {"matched_count": 0, "added_count": 0, "removed_count": 0}

    product_ids_for_query = [item.id for item in products]
    links_result = await db.execute(
        select(StoreCollectionProduct).where(
            StoreCollectionProduct.collection_id.in_([collection.id for collection in collections]),
            StoreCollectionProduct.published_product_id.in_(product_ids_for_query),
            StoreCollectionProduct.company_id == company_id,
        )
    )
    links_by_key = {
        (link.collection_id, link.published_product_id): link
        for link in links_result.scalars().all()
    }

    stats = {"matched_count": 0, "added_count": 0, "removed_count": 0}
    for collection in collections:
        collection_links = [link for link in links_by_key.values() if link.collection_id == collection.id]
        next_sort_order = max((link.sort_order or 0 for link in collection_links), default=-1) + 1
        for product in products:
            facts = product_rule_facts(product, getattr(product, "_collection_inventory", 0))
            key = (collection.id, product.id)
            link = links_by_key.get(key)
            matches = collection_matches_product(collection, facts)
            if matches:
                stats["matched_count"] += 1
                if link:
                    if not link.is_active:
                        link.is_active = True
                        link.updated_by_id = user_id
                        stats["added_count"] += 1
                else:
                    link = StoreCollectionProduct(
                        collection_id=collection.id,
                        published_product_id=product.id,
                        sort_order=next_sort_order,
                        company_id=company_id,
                        created_by_id=user_id,
                        updated_by_id=user_id,
                    )
                    db.add(link)
                    links_by_key[key] = link
                    collection_links.append(link)
                    next_sort_order += 1
                    stats["added_count"] += 1
            elif link and link.is_active:
                link.is_active = False
                link.updated_by_id = user_id
                stats["removed_count"] += 1
    return stats


async def reconcile_product_collections(
    db: AsyncSession,
    *,
    storefront_id: UUID,
    company_id: UUID,
    published_product_id: UUID,
    user_id: UUID | None = None,
) -> dict[str, int]:
    return await reconcile_automated_collections(
        db,
        storefront_id=storefront_id,
        company_id=company_id,
        user_id=user_id,
        product_ids=[published_product_id],
    )


async def reconcile_products_collections(
    db: AsyncSession,
    *,
    company_id: UUID,
    product_ids: list[UUID],
    user_id: UUID | None = None,
) -> dict[str, int]:
    """Reconcile all storefront publications for a group of ERP products."""
    if not product_ids:
        return {"matched_count": 0, "added_count": 0, "removed_count": 0}
    result = await db.execute(
        select(PublishedProduct.storefront_id, PublishedProduct.id).where(
            PublishedProduct.company_id == company_id,
            PublishedProduct.product_id.in_(product_ids),
            PublishedProduct.is_active == True,
        )
    )
    ids_by_storefront: dict[UUID, list[UUID]] = {}
    for storefront_id, published_product_id in result.all():
        ids_by_storefront.setdefault(storefront_id, []).append(published_product_id)

    stats = {"matched_count": 0, "added_count": 0, "removed_count": 0}
    for storefront_id, published_ids in ids_by_storefront.items():
        current = await reconcile_automated_collections(
            db,
            storefront_id=storefront_id,
            company_id=company_id,
            user_id=user_id,
            product_ids=published_ids,
        )
        for key in stats:
            stats[key] += current[key]
    return stats
