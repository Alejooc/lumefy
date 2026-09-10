from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable
from uuid import UUID

from sqlalchemy import false, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.storefront import StoreCollection, StoreCollectionProduct, StorefrontOrder
from app.models.storefront_promotion import StorefrontPromotion


@dataclass(frozen=True)
class PromotionContext:
    by_published_product: dict[UUID, StorefrontPromotion]


def promotion_value(promotion: StorefrontPromotion | None) -> float:
    if not promotion:
        return 0.0
    value = getattr(promotion, "discount_value", None)
    if value is None:
        value = getattr(promotion, "discount_percent", 0.0)
    return max(0.0, float(value or 0.0))


def choose_best_promotion(promotions: Iterable[StorefrontPromotion]) -> StorefrontPromotion | None:
    """Resolve overlapping product promotions without stacking them."""
    candidates = list(promotions)
    if not candidates:
        return None

    def sort_key(promotion: StorefrontPromotion) -> tuple[int, float, float, str]:
        created_at = promotion.created_at
        created_timestamp = created_at.timestamp() if created_at else 0.0
        return (
            int(promotion.priority or 0),
            promotion_value(promotion),
            created_timestamp,
            str(promotion.id),
        )

    return max(candidates, key=sort_key)


def apply_promotion(unit_price: float, promotion: StorefrontPromotion | None) -> tuple[float, float]:
    """Return (net price, discount amount) rounded to the storefront currency."""
    original = Decimal(str(max(0.0, float(unit_price or 0.0))))
    if (
        not promotion
        or getattr(promotion, "promotion_type", "AMOUNT_OFF") == "BUY_X_GET_Y"
        or getattr(promotion, "discount_type", "PERCENT") == "FREE_SHIPPING"
    ):
        return float(original), 0.0

    discount_type = getattr(promotion, "discount_type", "PERCENT")
    value = Decimal(str(promotion_value(promotion)))
    if discount_type == "FIXED":
        discount = value
    else:
        value = min(Decimal("100"), max(Decimal("0"), value))
        discount = original * value / Decimal("100")
    discount = min(original, max(Decimal("0"), discount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    net = (original - discount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(net), float(discount)


def calculate_order_promotion(subtotal: float, promotion: StorefrontPromotion | None) -> float:
    """Calculate a promotion targeting the complete order."""
    if not promotion or promotion.discount_type == "FREE_SHIPPING":
        return 0.0
    _net, discount = apply_promotion(subtotal, promotion)
    return discount


def meets_minimum_requirement(
    promotion: StorefrontPromotion,
    *,
    subtotal: float,
    quantity: float = 0,
) -> bool:
    requirement = getattr(promotion, "minimum_requirement", "NONE")
    if requirement == "AMOUNT":
        return subtotal >= float(getattr(promotion, "minimum_amount", 0) or 0)
    if requirement == "QUANTITY":
        return quantity >= float(getattr(promotion, "minimum_quantity", 0) or 0)
    return True


async def promotion_cart_totals(
    db: AsyncSession,
    promotion: StorefrontPromotion,
    rows: Iterable[object],
) -> tuple[float, float]:
    """Return (subtotal, quantity) for the products targeted by a promotion."""
    cart_rows = list(rows)
    if promotion.target_type in {"ORDER", "SHIPPING"}:
        eligible_rows = cart_rows
    elif promotion.target_type == "PRODUCT":
        eligible_rows = [
            row for row in cart_rows
            if getattr(row, "published_product_id", None) == promotion.published_product_id
        ]
    elif promotion.target_type == "COLLECTION" and promotion.collection_id:
        published_ids = [getattr(row, "published_product_id", None) for row in cart_rows]
        links_result = await db.execute(
            select(StoreCollectionProduct.published_product_id).where(
                StoreCollectionProduct.collection_id == promotion.collection_id,
                StoreCollectionProduct.published_product_id.in_([value for value in published_ids if value]),
                StoreCollectionProduct.is_active.is_(True),
                StoreCollectionProduct.is_excluded.is_(False),
            )
        )
        eligible_ids = {published_id for (published_id,) in links_result.all()}
        eligible_rows = [
            row for row in cart_rows
            if getattr(row, "published_product_id", None) in eligible_ids
        ]
    else:
        eligible_rows = []
    return (
        sum(float(getattr(row, "line_subtotal", 0) or 0) for row in eligible_rows),
        sum(float(getattr(row, "quantity", 0) or 0) for row in eligible_rows),
    )


def promotion_is_available(promotion: StorefrontPromotion, now: datetime | None = None) -> bool:
    current_time = now or datetime.now(timezone.utc)
    if not promotion.is_active or not promotion.is_enabled:
        return False
    if promotion.starts_at and promotion.starts_at > current_time:
        return False
    if promotion.ends_at and promotion.ends_at < current_time:
        return False
    if promotion.usage_limit is not None and promotion.usage_count >= promotion.usage_limit:
        return False
    return True


async def get_storefront_promotion_by_code(
    db: AsyncSession,
    storefront_id: UUID,
    code: str,
    *,
    now: datetime | None = None,
    customer_email: str | None = None,
) -> StorefrontPromotion | None:
    promotion = await db.scalar(
        select(StorefrontPromotion).where(
            StorefrontPromotion.storefront_id == storefront_id,
            StorefrontPromotion.method == "CODE",
            StorefrontPromotion.code == code.strip().upper(),
            StorefrontPromotion.is_active.is_(True),
            StorefrontPromotion.is_enabled.is_(True),
        )
    )
    if not promotion or not promotion_is_available(promotion, now):
        return None
    eligible = await filter_customer_eligible_promotions(db, [promotion], customer_email)
    return eligible[0] if eligible else None


async def load_storefront_order_promotion(
    db: AsyncSession,
    storefront_id: UUID,
    *,
    code: str | None = None,
    now: datetime | None = None,
    customer_email: str | None = None,
) -> StorefrontPromotion | None:
    current_time = now or datetime.now(timezone.utc)
    query = select(StorefrontPromotion).where(
        StorefrontPromotion.storefront_id == storefront_id,
        StorefrontPromotion.promotion_type == "AMOUNT_OFF",
        StorefrontPromotion.target_type == "ORDER",
        StorefrontPromotion.is_active.is_(True),
        StorefrontPromotion.is_enabled.is_(True),
        (StorefrontPromotion.starts_at.is_(None) | (StorefrontPromotion.starts_at <= current_time)),
        (StorefrontPromotion.ends_at.is_(None) | (StorefrontPromotion.ends_at >= current_time)),
    )
    if code:
        query = query.where(StorefrontPromotion.method == "CODE", StorefrontPromotion.code == code.strip().upper())
    else:
        query = query.where(StorefrontPromotion.method == "AUTOMATIC")
    result = await db.execute(query)
    promotions = [promotion for promotion in result.scalars().all() if promotion_is_available(promotion, current_time)]
    promotions = await filter_customer_eligible_promotions(db, promotions, customer_email)
    return choose_best_promotion(promotions)


async def load_storefront_shipping_promotion(
    db: AsyncSession,
    storefront_id: UUID,
    *,
    code: str | None = None,
    now: datetime | None = None,
    customer_email: str | None = None,
) -> StorefrontPromotion | None:
    current_time = now or datetime.now(timezone.utc)
    query = select(StorefrontPromotion).where(
        StorefrontPromotion.storefront_id == storefront_id,
        StorefrontPromotion.promotion_type == "AMOUNT_OFF",
        StorefrontPromotion.target_type == "SHIPPING",
        StorefrontPromotion.is_active.is_(True),
        StorefrontPromotion.is_enabled.is_(True),
        (StorefrontPromotion.starts_at.is_(None) | (StorefrontPromotion.starts_at <= current_time)),
        (StorefrontPromotion.ends_at.is_(None) | (StorefrontPromotion.ends_at >= current_time)),
    )
    if code:
        query = query.where(StorefrontPromotion.method == "CODE", StorefrontPromotion.code == code.strip().upper())
    else:
        query = query.where(StorefrontPromotion.method == "AUTOMATIC")
    result = await db.execute(query)
    promotions = [promotion for promotion in result.scalars().all() if promotion_is_available(promotion, current_time)]
    promotions = await filter_customer_eligible_promotions(db, promotions, customer_email)
    return choose_best_promotion(promotions)


async def load_storefront_buy_x_get_y_promotions(
    db: AsyncSession,
    storefront_id: UUID,
    *,
    code: str | None = None,
    now: datetime | None = None,
    customer_email: str | None = None,
) -> list[StorefrontPromotion]:
    """Load active Buy X Get Y rules for the storefront/cart."""
    current_time = now or datetime.now(timezone.utc)
    query = select(StorefrontPromotion).where(
        StorefrontPromotion.storefront_id == storefront_id,
        StorefrontPromotion.promotion_type == "BUY_X_GET_Y",
        StorefrontPromotion.target_type.in_(["COLLECTION", "PRODUCT"]),
        StorefrontPromotion.is_active.is_(True),
        StorefrontPromotion.is_enabled.is_(True),
        (StorefrontPromotion.starts_at.is_(None) | (StorefrontPromotion.starts_at <= current_time)),
        (StorefrontPromotion.ends_at.is_(None) | (StorefrontPromotion.ends_at >= current_time)),
    )
    if code:
        query = query.where(
            or_(
                StorefrontPromotion.method == "AUTOMATIC",
                (StorefrontPromotion.method == "CODE")
                & (StorefrontPromotion.code == code.strip().upper()),
            )
        )
    else:
        query = query.where(StorefrontPromotion.method == "AUTOMATIC")
    result = await db.execute(query.order_by(StorefrontPromotion.priority.desc(), StorefrontPromotion.created_at.desc()))
    promotions = [promotion for promotion in result.scalars().all() if promotion_is_available(promotion, current_time)]
    return await filter_customer_eligible_promotions(db, promotions, customer_email)


async def _promotion_target_ids(
    db: AsyncSession,
    promotion: StorefrontPromotion,
    published_product_ids: list[UUID],
    *,
    reward: bool = False,
) -> set[UUID]:
    target_type = promotion.reward_target_type if reward else promotion.target_type
    product_id = promotion.reward_published_product_id if reward else promotion.published_product_id
    collection_id = promotion.reward_collection_id if reward else promotion.collection_id
    if target_type == "PRODUCT" and product_id in published_product_ids:
        return {product_id}
    if target_type != "COLLECTION" or not collection_id:
        return set()
    result = await db.execute(
        select(StoreCollectionProduct.published_product_id).where(
            StoreCollectionProduct.collection_id == collection_id,
            StoreCollectionProduct.published_product_id.in_(published_product_ids),
            StoreCollectionProduct.is_active.is_(True),
            StoreCollectionProduct.is_excluded.is_(False),
        )
    )
    return {published_id for (published_id,) in result.all()}


def _buy_get_discount(unit_price: float, promotion: StorefrontPromotion) -> float:
    value = Decimal(str(max(0.0, float(promotion.get_discount_value or 0.0))))
    original = Decimal(str(max(0.0, float(unit_price or 0.0))))
    if promotion.get_discount_type == "FIXED":
        discount = value
    else:
        discount = original * min(Decimal("100"), value) / Decimal("100")
    return float(min(original, max(Decimal("0"), discount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


async def apply_buy_x_get_y_promotions(
    db: AsyncSession,
    rows: list[object],
    promotions: list[StorefrontPromotion],
) -> None:
    """Apply Buy X Get Y discounts to the cheapest eligible reward units."""
    if not rows or not promotions:
        return
    published_ids = list({getattr(row, "published_product_id", None) for row in rows if getattr(row, "published_product_id", None)})
    if not published_ids:
        return

    explicit = [promotion for promotion in promotions if promotion.method == "CODE"]
    if explicit:
        automatic = [promotion for promotion in promotions if promotion.method == "AUTOMATIC"]
        selected = choose_best_promotion(explicit)
        promotions = [selected] if selected else []
        if selected and selected.combines_with_product:
            promotions.extend(
                promotion for promotion in automatic
                if promotion.method == "AUTOMATIC" and promotion.combines_with_product
            )
    elif any(not promotion.combines_with_product for promotion in promotions):
        selected = choose_best_promotion(promotions)
        promotions = [selected] if selected else []

    for promotion in promotions:
        buy_ids = await _promotion_target_ids(db, promotion, published_ids)
        reward_ids = await _promotion_target_ids(db, promotion, published_ids, reward=True)
        promotion_subtotal, promotion_quantity = await promotion_cart_totals(db, promotion, rows)
        if not meets_minimum_requirement(
            promotion,
            subtotal=promotion_subtotal,
            quantity=promotion_quantity,
        ):
            continue
        buy_quantity = sum(
            float(getattr(row, "quantity", 0) or 0)
            for row in rows
            if getattr(row, "published_product_id", None) in buy_ids
        )
        reward_rows = [
            row for row in rows
            if getattr(row, "published_product_id", None) in reward_ids
        ]
        if not reward_rows:
            continue
        same_scope = buy_ids == reward_ids
        divisor = promotion.buy_quantity + promotion.get_quantity if same_scope else promotion.buy_quantity
        reward_quantity = min(
            sum(float(getattr(row, "quantity", 0) or 0) for row in reward_rows),
            (int(buy_quantity // divisor) * promotion.get_quantity),
        )
        if reward_quantity <= 0:
            continue
        remaining = float(reward_quantity)
        for row in sorted(reward_rows, key=lambda item: float(getattr(item, "unit_price", 0) or 0)):
            if remaining <= 0:
                break
            units = min(float(getattr(row, "quantity", 0) or 0), remaining)
            extra_discount = _buy_get_discount(float(getattr(row, "unit_price", 0) or 0), promotion) * units
            if extra_discount <= 0:
                continue
            row.line_subtotal = max(0.0, float(row.line_subtotal or 0) - extra_discount)
            row.unit_price = round(float(row.line_subtotal) / float(row.quantity), 2) if row.quantity else 0.0
            row.promotion_discount_amount = (
                float(row.promotion_discount_amount or 0)
                + extra_discount / float(row.quantity)
            )
            row.promotion_name = (
                f"{row.promotion_name} + {promotion.name}"
                if row.promotion_name and row.promotion.name not in row.promotion_name
                else promotion.name
            )
            row.promotion_discount_type = promotion.get_discount_type
            row.promotion_discount_value = float(promotion.get_discount_value)
            row.promotion_discount_percent = (
                float(promotion.get_discount_value)
                if promotion.get_discount_type == "PERCENT"
                else None
            )
            remaining -= units


async def load_storefront_promotion_context(
    db: AsyncSession,
    storefront_id: UUID,
    published_product_ids: list[UUID],
    *,
    now: datetime | None = None,
    code: str | None = None,
    include_automatic: bool = True,
    include_minimum: bool = False,
    customer_email: str | None = None,
) -> PromotionContext:
    if not published_product_ids:
        return PromotionContext(by_published_product={})

    current_time = now or datetime.now(timezone.utc)
    method_filter = StorefrontPromotion.method == "AUTOMATIC" if include_automatic else false()
    if code:
        code_filter = (StorefrontPromotion.method == "CODE") & (
            StorefrontPromotion.code == code.strip().upper()
        )
        method_filter = or_(StorefrontPromotion.method == "AUTOMATIC", code_filter) if include_automatic else code_filter
    promotions_result = await db.execute(
        select(StorefrontPromotion).where(
            StorefrontPromotion.storefront_id == storefront_id,
            StorefrontPromotion.promotion_type == "AMOUNT_OFF",
            StorefrontPromotion.is_active.is_(True),
            StorefrontPromotion.is_enabled.is_(True),
            (StorefrontPromotion.starts_at.is_(None) | (StorefrontPromotion.starts_at <= current_time)),
            (StorefrontPromotion.ends_at.is_(None) | (StorefrontPromotion.ends_at >= current_time)),
            method_filter,
        )
    )
    all_promotions = promotions_result.scalars().all()
    promotions = [promotion for promotion in all_promotions if promotion_is_available(promotion, current_time)]
    promotions = await filter_customer_eligible_promotions(db, promotions, customer_email)
    if not include_minimum:
        promotions = [promotion for promotion in promotions if promotion.minimum_requirement == "NONE"]
    if code:
        code_promotions = [
            promotion for promotion in promotions
            if promotion.method == "CODE"
            and promotion.code == code.strip().upper()
            and (include_minimum or promotion.minimum_requirement == "NONE")
        ]
        if include_automatic:
            promotions = [promotion for promotion in promotions if promotion.method == "AUTOMATIC"] + code_promotions
        else:
            promotions = code_promotions
    if not promotions:
        return PromotionContext(by_published_product={})

    candidates: dict[UUID, list[StorefrontPromotion]] = {}
    for promotion in promotions:
        if promotion.target_type == "PRODUCT" and promotion.published_product_id in published_product_ids:
            candidates.setdefault(promotion.published_product_id, []).append(promotion)

    collection_promotions = [promotion for promotion in promotions if promotion.target_type == "COLLECTION" and promotion.collection_id]
    if collection_promotions:
        collection_ids = [promotion.collection_id for promotion in collection_promotions]
        links_result = await db.execute(
            select(StoreCollectionProduct.collection_id, StoreCollectionProduct.published_product_id)
            .join(StoreCollection, StoreCollection.id == StoreCollectionProduct.collection_id)
            .where(
                StoreCollectionProduct.collection_id.in_(collection_ids),
                StoreCollectionProduct.published_product_id.in_(published_product_ids),
                StoreCollectionProduct.is_active.is_(True),
                StoreCollectionProduct.is_excluded.is_(False),
                StoreCollection.storefront_id == storefront_id,
                StoreCollection.is_active.is_(True),
            )
        )
        collection_promotions_by_id = {
            promotion.collection_id: promotion
            for promotion in collection_promotions
        }
        for collection_id, published_product_id in links_result.all():
            promotion = collection_promotions_by_id.get(collection_id)
            if promotion:
                candidates.setdefault(published_product_id, []).append(promotion)

    return PromotionContext(
        by_published_product={
            published_product_id: selected
            for published_product_id, options in candidates.items()
            if (selected := choose_best_promotion(options)) is not None
        }
    )


async def customer_has_storefront_order(
    db: AsyncSession,
    storefront_id: UUID,
    customer_email: str | None,
) -> bool:
    normalized_email = (customer_email or "").strip().lower()
    if not normalized_email:
        return False
    order_id = await db.scalar(
        select(StorefrontOrder.id)
        .where(
            StorefrontOrder.storefront_id == storefront_id,
            func.lower(func.trim(StorefrontOrder.customer_email)) == normalized_email,
            StorefrontOrder.is_active.is_(True),
        )
        .limit(1)
    )
    return order_id is not None


async def filter_customer_eligible_promotions(
    db: AsyncSession,
    promotions: Iterable[StorefrontPromotion],
    customer_email: str | None,
) -> list[StorefrontPromotion]:
    candidates = list(promotions)
    if not candidates:
        return []
    restricted = [
        promotion
        for promotion in candidates
        if getattr(promotion, "customer_eligibility", "ALL") != "ALL"
    ]
    if not restricted:
        return candidates
    normalized_email = (customer_email or "").strip()
    if not normalized_email:
        return [
            promotion
            for promotion in candidates
            if getattr(promotion, "customer_eligibility", "ALL") == "ALL"
        ]
    has_previous_order = await customer_has_storefront_order(
        db,
        candidates[0].storefront_id,
        normalized_email,
    )
    return [
        promotion
        for promotion in candidates
        if getattr(promotion, "customer_eligibility", "ALL") == "ALL"
        or (
            getattr(promotion, "customer_eligibility", "ALL") == "RETURNING_CUSTOMERS"
            and has_previous_order
        )
        or (
            getattr(promotion, "customer_eligibility", "ALL") == "NEW_CUSTOMERS"
            and not has_previous_order
        )
    ]


async def customer_has_used_code(
    db: AsyncSession,
    promotion: StorefrontPromotion,
    customer_email: str | None,
) -> bool:
    if not customer_email or not promotion.code:
        return False
    count = await db.scalar(
        select(StorefrontOrder.id)
        .where(
            StorefrontOrder.storefront_id == promotion.storefront_id,
            func.lower(StorefrontOrder.coupon_code) == promotion.code.lower(),
            StorefrontOrder.customer_email.ilike(customer_email.strip()),
            StorefrontOrder.is_active.is_(True),
        )
        .limit(1)
    )
    return count is not None


async def consume_code_usage(db: AsyncSession, promotion: StorefrontPromotion) -> None:
    result = await db.execute(
        update(StorefrontPromotion)
        .where(
            StorefrontPromotion.id == promotion.id,
            StorefrontPromotion.is_active.is_(True),
            StorefrontPromotion.is_enabled.is_(True),
            (
                StorefrontPromotion.usage_limit.is_(None)
                | (StorefrontPromotion.usage_count < StorefrontPromotion.usage_limit)
            ),
        )
        .values(usage_count=StorefrontPromotion.usage_count + 1)
    )
    if result.rowcount != 1:
        raise ValueError("La promoción alcanzó su límite de usos")
