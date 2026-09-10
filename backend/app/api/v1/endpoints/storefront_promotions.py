from datetime import datetime
from typing import List
from uuid import UUID, uuid4

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
    if target_type in {"ORDER", "SHIPPING"}:
        if collection_id is not None or published_product_id is not None:
            raise HTTPException(status_code=400, detail="Las promociones de pedido o envío no llevan un objetivo")
        return ("Pedido completo" if target_type == "ORDER" else "Envío"), None
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
    raise HTTPException(status_code=400, detail="Tipo de promoción no soportado")


async def _ensure_code_available(
    db: AsyncSession,
    *,
    storefront_id: UUID,
    method: str,
    code: str | None,
    promotion_id: UUID | None = None,
) -> None:
    if method != "CODE":
        return
    if not code:
        raise HTTPException(status_code=400, detail="Las promociones con código necesitan un código")
    query = select(StorefrontPromotion.id).where(
        StorefrontPromotion.storefront_id == storefront_id,
        StorefrontPromotion.code == code,
        StorefrontPromotion.is_active.is_(True),
    )
    if promotion_id:
        query = query.where(StorefrontPromotion.id != promotion_id)
    if await db.scalar(query):
        raise HTTPException(status_code=409, detail="Ya existe una promoción activa con ese código")


def _serialize(promotion: StorefrontPromotion) -> schemas.PromotionOut:
    collection_name = promotion.collection.name if promotion.collection else None
    product_name = (
        promotion.published_product.product.name
        if promotion.published_product and promotion.published_product.product
        else None
    )
    reward_collection_name = promotion.reward_collection.name if promotion.reward_collection else None
    reward_product_name = (
        promotion.reward_published_product.product.name
        if promotion.reward_published_product and promotion.reward_published_product.product
        else None
    )
    if promotion.target_type == "COLLECTION":
        target_label = collection_name or "Colección"
    elif promotion.target_type == "ORDER":
        target_label = "Pedido completo"
    elif promotion.target_type == "SHIPPING":
        target_label = "Envío"
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
        method=promotion.method,
        code=promotion.code,
        promotion_type=promotion.promotion_type,
        target_type=promotion.target_type,
        collection_id=promotion.collection_id,
        published_product_id=promotion.published_product_id,
        collection_name=collection_name,
        product_name=product_name,
        reward_target_type=promotion.reward_target_type,
        reward_collection_id=promotion.reward_collection_id,
        reward_published_product_id=promotion.reward_published_product_id,
        reward_collection_name=reward_collection_name,
        reward_product_name=reward_product_name,
        buy_quantity=promotion.buy_quantity,
        get_quantity=promotion.get_quantity,
        get_discount_type=promotion.get_discount_type,
        get_discount_value=float(promotion.get_discount_value),
        target_label=target_label,
        discount_type=promotion.discount_type,
        discount_value=float(promotion.discount_value),
        discount_percent=promotion.discount_percent,
        priority=promotion.priority,
        minimum_requirement=promotion.minimum_requirement,
        minimum_amount=float(promotion.minimum_amount or 0),
        minimum_quantity=promotion.minimum_quantity or 0,
        usage_limit=promotion.usage_limit,
        usage_count=promotion.usage_count or 0,
        once_per_customer=promotion.once_per_customer,
        combines_with_product=promotion.combines_with_product,
        combines_with_order=promotion.combines_with_order,
        combines_with_shipping=promotion.combines_with_shipping,
        customer_eligibility=promotion.customer_eligibility,
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
            selectinload(StorefrontPromotion.reward_collection),
            selectinload(StorefrontPromotion.reward_published_product).selectinload(PublishedProduct.product),
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
    await _validate_target(
        db,
        storefront_id=data.storefront_id,
        target_type=data.target_type,
        collection_id=data.collection_id,
        published_product_id=data.published_product_id,
    )
    if data.promotion_type == "BUY_X_GET_Y":
        await _validate_target(
            db,
            storefront_id=data.storefront_id,
            target_type=data.reward_target_type,
            collection_id=data.reward_collection_id,
            published_product_id=data.reward_published_product_id,
        )
    _validate_dates(data.starts_at, data.ends_at)
    await _ensure_code_available(
        db,
        storefront_id=data.storefront_id,
        method=data.method,
        code=data.code,
    )
    values = data.model_dump()
    values["discount_percent"] = data.discount_percent
    promotion = StorefrontPromotion(
        **values,
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
        details={
            "name": promotion.name,
            "target_type": promotion.target_type,
            "method": promotion.method,
            "discount_type": promotion.discount_type,
            "discount_value": promotion.discount_value,
        },
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
        collection_id = None if target_type in {"PRODUCT", "ORDER", "SHIPPING"} else promotion.collection_id
        published_product_id = None if target_type in {"COLLECTION", "ORDER", "SHIPPING"} else promotion.published_product_id
    if target_type in {"ORDER", "SHIPPING"}:
        collection_id = None
        published_product_id = None
    promotion_type = values.get("promotion_type", promotion.promotion_type)
    reward_target_type = values.get("reward_target_type", promotion.reward_target_type)
    reward_collection_id = values.get("reward_collection_id", promotion.reward_collection_id)
    reward_published_product_id = values.get(
        "reward_published_product_id", promotion.reward_published_product_id
    )
    if promotion_type == "BUY_X_GET_Y":
        if target_type not in {"COLLECTION", "PRODUCT"}:
            raise HTTPException(
                status_code=400,
                detail="Compra X y lleva Y necesita productos o una colección como condición",
            )
        if reward_target_type is None:
            reward_target_type = target_type
        if "reward_target_type" in values and not {
            "reward_collection_id",
            "reward_published_product_id",
        }.intersection(values):
            reward_collection_id = None
            reward_published_product_id = None
        if reward_collection_id is None and reward_published_product_id is None:
            reward_collection_id = collection_id if reward_target_type == "COLLECTION" else None
            reward_published_product_id = published_product_id if reward_target_type == "PRODUCT" else None
        if reward_target_type == "COLLECTION":
            reward_published_product_id = None
        elif reward_target_type == "PRODUCT":
            reward_collection_id = None
        else:
            raise HTTPException(status_code=400, detail="La recompensa necesita colección o producto")
    else:
        reward_target_type = None
        reward_collection_id = None
        reward_published_product_id = None
    method = values.get("method", promotion.method)
    code = values.get("code", promotion.code)
    if method == "CODE":
        code = (code or "").strip().upper() or None
    else:
        code = None
    if promotion_type == "BUY_X_GET_Y":
        discount_type = "PERCENT"
        discount_value = 100
        get_discount_type = values.get("get_discount_type", promotion.get_discount_type)
        get_discount_value = values.get("get_discount_value", promotion.get_discount_value)
        if get_discount_type == "PERCENT" and not 0 < float(get_discount_value) <= 100:
            raise HTTPException(status_code=400, detail="El porcentaje de la recompensa debe estar entre 0,01 y 100")
        if get_discount_type == "FIXED" and float(get_discount_value) <= 0:
            raise HTTPException(status_code=400, detail="El descuento fijo de la recompensa debe ser mayor que cero")
    else:
        discount_type = values.get("discount_type", promotion.discount_type)
        discount_value = values.get("discount_value")
        if discount_value is None and "discount_percent" in values:
            discount_value = values["discount_percent"]
        if discount_value is None:
            discount_value = promotion.discount_value
        if discount_type == "FREE_SHIPPING":
            discount_value = 0
        if discount_type == "PERCENT" and not 0 < float(discount_value) <= 100:
            raise HTTPException(status_code=400, detail="El porcentaje debe estar entre 0,01 y 100")
        if discount_type == "FIXED" and float(discount_value) <= 0:
            raise HTTPException(status_code=400, detail="El descuento fijo debe ser mayor que cero")
        if target_type == "SHIPPING" and discount_type != "FREE_SHIPPING":
            raise HTTPException(status_code=400, detail="Una promoción de envío debe ser de envío gratis")
        if target_type != "SHIPPING" and discount_type == "FREE_SHIPPING":
            raise HTTPException(status_code=400, detail="El envío gratis solo aplica al objetivo de envío")
    minimum_requirement = values.get("minimum_requirement", promotion.minimum_requirement)
    minimum_amount = values.get("minimum_amount", promotion.minimum_amount)
    minimum_quantity = values.get("minimum_quantity", promotion.minimum_quantity)
    if minimum_requirement == "AMOUNT" and not float(minimum_amount or 0) > 0:
        raise HTTPException(status_code=400, detail="Indica un monto mínimo mayor que cero")
    if minimum_requirement == "QUANTITY" and not int(minimum_quantity or 0) > 0:
        raise HTTPException(status_code=400, detail="Indica una cantidad mínima mayor que cero")
    await _validate_target(
        db,
        storefront_id=storefront_id,
        target_type=target_type,
        collection_id=collection_id,
        published_product_id=published_product_id,
    )
    if promotion_type == "BUY_X_GET_Y":
        await _validate_target(
            db,
            storefront_id=storefront_id,
            target_type=reward_target_type,
            collection_id=reward_collection_id,
            published_product_id=reward_published_product_id,
        )
    starts_at = values.get("starts_at", promotion.starts_at)
    ends_at = values.get("ends_at", promotion.ends_at)
    _validate_dates(starts_at, ends_at)
    await _ensure_code_available(
        db,
        storefront_id=storefront_id,
        method=method,
        code=code,
        promotion_id=promotion.id,
    )
    for field, field_value in values.items():
        if field in {
            "discount_percent",
            "discount_value",
            "method",
            "code",
            "collection_id",
            "published_product_id",
            "target_type",
            "promotion_type",
            "reward_target_type",
            "reward_collection_id",
            "reward_published_product_id",
            "get_discount_type",
            "get_discount_value",
        }:
            continue
        setattr(promotion, field, field_value)
    promotion.storefront_id = storefront_id
    promotion.method = method
    promotion.code = code
    promotion.target_type = target_type
    promotion.collection_id = collection_id
    promotion.published_product_id = published_product_id
    promotion.promotion_type = promotion_type
    promotion.reward_target_type = reward_target_type
    promotion.reward_collection_id = reward_collection_id
    promotion.reward_published_product_id = reward_published_product_id
    promotion.discount_type = discount_type
    promotion.discount_value = discount_value
    promotion.discount_percent = discount_value if discount_type == "PERCENT" else None
    if promotion_type == "BUY_X_GET_Y":
        promotion.get_discount_type = get_discount_type
        promotion.get_discount_value = get_discount_value
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


@router.post("/{promotion_id}/duplicate", response_model=schemas.PromotionOut)
async def duplicate_promotion(
    promotion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
):
    result = await db.execute(_promotion_query(current_user.company_id).where(StorefrontPromotion.id == promotion_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Promoción no encontrada")

    duplicate_code = None
    if source.method == "CODE":
        duplicate_code = f"COPIA-{uuid4().hex[:8].upper()}"
        await _ensure_code_available(
            db,
            storefront_id=source.storefront_id,
            method=source.method,
            code=duplicate_code,
        )
    duplicate = StorefrontPromotion(
        storefront_id=source.storefront_id,
        company_id=current_user.company_id,
        name=f"{source.name[:111]} · copia",
        target_type=source.target_type,
        collection_id=source.collection_id,
        published_product_id=source.published_product_id,
        promotion_type=source.promotion_type,
        reward_target_type=source.reward_target_type,
        reward_collection_id=source.reward_collection_id,
        reward_published_product_id=source.reward_published_product_id,
        buy_quantity=source.buy_quantity,
        get_quantity=source.get_quantity,
        get_discount_type=source.get_discount_type,
        get_discount_value=source.get_discount_value,
        method=source.method,
        code=duplicate_code,
        discount_type=source.discount_type,
        discount_value=source.discount_value,
        discount_percent=source.discount_percent,
        minimum_requirement=source.minimum_requirement,
        minimum_amount=source.minimum_amount,
        minimum_quantity=source.minimum_quantity,
        usage_limit=source.usage_limit,
        once_per_customer=source.once_per_customer,
        combines_with_product=source.combines_with_product,
        combines_with_order=source.combines_with_order,
        combines_with_shipping=source.combines_with_shipping,
        customer_eligibility=source.customer_eligibility,
        priority=source.priority,
        starts_at=source.starts_at,
        ends_at=source.ends_at,
        is_enabled=False,
        created_by_id=current_user.id,
    )
    db.add(duplicate)
    await db.flush()
    await log_activity(
        db,
        action="CREATE",
        entity_type="StorefrontPromotion",
        entity_id=duplicate.id,
        user_id=current_user.id,
        company_id=current_user.company_id,
        details={"name": duplicate.name, "duplicated_from": str(source.id)},
    )
    await db.commit()
    result = await db.execute(_promotion_query(current_user.company_id).where(StorefrontPromotion.id == duplicate.id))
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
