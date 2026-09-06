from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.storefront import StoreCollection, StoreCollectionProduct
from app.models.storefront_promotion import StorefrontPromotion


@dataclass(frozen=True)
class PromotionContext:
    by_published_product: dict[UUID, StorefrontPromotion]


def choose_best_promotion(promotions: Iterable[StorefrontPromotion]) -> StorefrontPromotion | None:
    """Resolve overlaps without stacking discounts.

    Priority wins first; discount and creation time make the result stable for
    promotions configured at the same priority.
    """
    candidates = list(promotions)
    if not candidates:
        return None

    def sort_key(promotion: StorefrontPromotion) -> tuple[int, float, float, str]:
        created_at = promotion.created_at
        created_timestamp = created_at.timestamp() if created_at else 0.0
        return (
            int(promotion.priority or 0),
            float(promotion.discount_percent or 0.0),
            created_timestamp,
            str(promotion.id),
        )

    return max(candidates, key=sort_key)


def apply_promotion(unit_price: float, promotion: StorefrontPromotion | None) -> tuple[float, float]:
    """Return (net price, discount amount) rounded to the storefront currency."""
    original = Decimal(str(max(0.0, float(unit_price or 0.0))))
    if not promotion:
        return float(original), 0.0
    percent = Decimal(str(max(0.0, min(100.0, float(promotion.discount_percent or 0.0)))))
    discount = (original * percent / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    discount = min(original, max(Decimal("0"), discount))
    net = (original - discount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(net), float(discount)


async def load_storefront_promotion_context(
    db: AsyncSession,
    storefront_id: UUID,
    published_product_ids: list[UUID],
    *,
    now: datetime | None = None,
) -> PromotionContext:
    if not published_product_ids:
        return PromotionContext(by_published_product={})

    current_time = now or datetime.now(timezone.utc)
    promotions_result = await db.execute(
        select(StorefrontPromotion).where(
            StorefrontPromotion.storefront_id == storefront_id,
            StorefrontPromotion.is_active.is_(True),
            StorefrontPromotion.is_enabled.is_(True),
            (StorefrontPromotion.starts_at.is_(None) | (StorefrontPromotion.starts_at <= current_time)),
            (StorefrontPromotion.ends_at.is_(None) | (StorefrontPromotion.ends_at >= current_time)),
        )
    )
    promotions = promotions_result.scalars().all()
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
