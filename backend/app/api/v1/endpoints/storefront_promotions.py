from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import log_activity
from app.core.database import get_db
from app.core.permissions import PermissionChecker
from app.models.storefront import PublishedProduct, StoreCollection, Storefront
from app.models.storefront_promotion import StorefrontPromotion
from app.models.user import User
from app.schemas import storefront_promotion as schemas

router = APIRouter()


async def _get_company_storefront(db: AsyncSession, storefront_id: UUID, company_id: UUID) -> Storefront:
    storefront = await db.scalar(
        select(Storefront).where(
            Storefront.id == storefront_id,
            Storefront.company_id == company_id,
            Storefront.is_active.is_(True),
        )
    )
    if not storefront:
        raise HTTPException(status_code=404, detail="Tienda no encontrada")
    return storefront


async def _validate_target(
    db: AsyncSession,
    *,
    storefront_id: UUID,
    target_type: str,
    collection_id: UUID | None,
    published_product_id: UUID | None,
) -> tuple[str | None, str | None]:
    if (collection_id is not None) == (published_product_id is not None):
        raise HTTPException(status_code=400, detail="Selecciona exactamente una colección o un producto")
    if target_type == "COLLECTION":
        if collection_id is None:
            raise HTTPException(status_code=400, detail="Una promoción de colección necesita una colección")
        collection = await db.scalar(
            select(StoreCollection).where(
                StoreCollection.id == collection_id,
                StoreCollection.storefront_id == storefront_id,
                StoreCollection.is_active.is_(True),
            )
        )
        if not collection:
            raise HTTPException(status_code=404, detail="Colección no encontrada en esta tienda")
        return collection.name, None
    if target_type == "PRODUCT":
        if published_product_id is None:
            raise HTTPException(status_code=400, detail="Una promoción de producto necesita un producto")
        published_product = await db.scalar(
            select(PublishedProduct)
            .options(selectinload(PublishedProduct.product))
            .where(
                PublishedProduct.id == published_product_id,
                PublishedProduct.storefront_id == storefront_id,
                PublishedProduct.is_active.is_(True),
                PublishedProduct.is_published.is_(True),
            )
        )
        if not published_product:
            raise HTTPException(status_code=404, detail="Producto publicado no encontrado en esta tienda")
        return None, published_product.product.name if published_product.product else published_product.slug
    raise HTTPException(status_code=400, detail="El tipo de promoción debe ser COLLECTION o PRODUCT")


def _serialize(promotion: StorefrontPromotion) -> schemas.PromotionOut:
    collection_name = promotion.collection.name if promotion.collection else None
    product_name = (
        promotion.published_product.product.name
        if promotion.published_product and promotion.published_product.product
        else None
    )
    if promotion.target_type == "COLLECTION":
        target_label = collection_name or "Colección"
    elif product_name:
        target_label = product_name
    elif promotion.published_product:
        target_label = promotion.published_product.slug
    else:
        target_label = "Producto"
    return schemas.PromotionOut(
        id=promotion.id,
        storefront_id=promotion.storefront_id,
        name=promotion.name,
        target_type=promotion.target_type,
        collection_id=promotion.collection_id,
        published_product_id=promotion.published_product_id,
        collection_name=collection_name,
        product_name=product_name,
        target_label=target_label,
        discount_percent=promotion.discount_percent,
        priority=promotion.priority,
        starts_at=promotion.starts_at,
        ends_at=promotion.ends_at,
        is_enabled=promotion.is_enabled,
        is_active=promotion.is_active,
        created_at=promotion.created_at,
        updated_at=promotion.updated_at,
    )


def _validate_dates(starts_at: datetime | None, ends_at: datetime | None) -> None:
    if starts_at and ends_at and starts_at > ends_at:
        raise HTTPException(status_code=400, detail="La fecha inicial no puede ser posterior a la fecha final")


def _promotion_query(company_id: UUID):
    return (
        select(StorefrontPromotion)
        .options(
            selectinload(StorefrontPromotion.collection),
            selectinload(StorefrontPromotion.published_product).selectinload(PublishedProduct.product),
        )
        .where(
            StorefrontPromotion.company_id == company_id,
            StorefrontPromotion.is_active.is_(True),
        )
    )


@router.get("/", response_model=List[schemas.PromotionOut])
async def list_promotions(
    storefront_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
):
    query = _promotion_query(current_user.company_id)
    if storefront_id:
        query = query.where(StorefrontPromotion.storefront_id == storefront_id)
    result = await db.execute(query.order_by(StorefrontPromotion.priority.desc(), StorefrontPromotion.created_at.desc()))
    return [_serialize(promotion) for promotion in result.scalars().all()]


@router.post("/", response_model=schemas.PromotionOut)
async def create_promotion(
    data: schemas.PromotionIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
):
    await _get_company_storefront(db, data.storefront_id, current_user.company_id)
    collection_name, product_name = await _validate_target(
        db,
        storefront_id=data.storefront_id,
        target_type=data.target_type,
        collection_id=data.collection_id,
        published_product_id=data.published_product_id,
    )
    _validate_dates(data.starts_at, data.ends_at)
    promotion = StorefrontPromotion(
        **data.model_dump(),
        company_id=current_user.company_id,
        created_by_id=current_user.id,
    )
    db.add(promotion)
    await db.flush()
    await log_activity(
        db,
        action="CREATE",
        entity_type="StorefrontPromotion",
        entity_id=promotion.id,
        user_id=current_user.id,
        company_id=current_user.company_id,
        details={"name": promotion.name, "target_type": promotion.target_type, "discount_percent": promotion.discount_percent},
    )
    await db.commit()
    result = await db.execute(_promotion_query(current_user.company_id).where(StorefrontPromotion.id == promotion.id))
    return _serialize(result.scalar_one())


@router.put("/{promotion_id}", response_model=schemas.PromotionOut)
async def update_promotion(
    promotion_id: UUID,
    data: schemas.PromotionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
):
    promotion = await db.scalar(
        select(StorefrontPromotion).where(
            StorefrontPromotion.id == promotion_id,
            StorefrontPromotion.company_id == current_user.company_id,
            StorefrontPromotion.is_active.is_(True),
        )
    )
    if not promotion:
        raise HTTPException(status_code=404, detail="Promoción no encontrada")
    values = data.model_dump(exclude_unset=True)
    storefront_id = values.get("storefront_id", promotion.storefront_id)
    await _get_company_storefront(db, storefront_id, current_user.company_id)
    target_type = values.get("target_type", promotion.target_type)
    collection_id = values.get("collection_id", promotion.collection_id)
    published_product_id = values.get("published_product_id", promotion.published_product_id)
    if "target_type" in values and "collection_id" not in values and "published_product_id" not in values:
        collection_id = None if target_type == "PRODUCT" else promotion.collection_id
        published_product_id = None if target_type == "COLLECTION" else promotion.published_product_id
    await _validate_target(
        db,
        storefront_id=storefront_id,
        target_type=target_type,
        collection_id=collection_id,
        published_product_id=published_product_id,
    )
    starts_at = values.get("starts_at", promotion.starts_at)
    ends_at = values.get("ends_at", promotion.ends_at)
    _validate_dates(starts_at, ends_at)
    for field, field_value in values.items():
        setattr(promotion, field, field_value)
    promotion.storefront_id = storefront_id
    promotion.target_type = target_type
    promotion.collection_id = collection_id
    promotion.published_product_id = published_product_id
    promotion.updated_by_id = current_user.id
    await log_activity(
        db,
        action="UPDATE",
        entity_type="StorefrontPromotion",
        entity_id=promotion.id,
        user_id=current_user.id,
        company_id=current_user.company_id,
        details={"name": promotion.name, "fields": list(values)},
    )
    await db.commit()
    result = await db.execute(_promotion_query(current_user.company_id).where(StorefrontPromotion.id == promotion.id))
    return _serialize(result.scalar_one())


@router.delete("/{promotion_id}", response_model=schemas.PromotionOut)
async def disable_promotion(
    promotion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
):
    promotion = await db.scalar(
        select(StorefrontPromotion).where(
            StorefrontPromotion.id == promotion_id,
            StorefrontPromotion.company_id == current_user.company_id,
            StorefrontPromotion.is_active.is_(True),
        )
    )
    if not promotion:
        raise HTTPException(status_code=404, detail="Promoción no encontrada")
    promotion.is_enabled = False
    promotion.updated_by_id = current_user.id
    await log_activity(
        db,
        action="DISABLE",
        entity_type="StorefrontPromotion",
        entity_id=promotion.id,
        user_id=current_user.id,
        company_id=current_user.company_id,
        details={"name": promotion.name},
    )
    await db.commit()
    result = await db.execute(_promotion_query(current_user.company_id).where(StorefrontPromotion.id == promotion.id))
    return _serialize(result.scalar_one())
