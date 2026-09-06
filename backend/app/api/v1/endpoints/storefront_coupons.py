from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_activity
from app.core.database import get_db
from app.core.permissions import PermissionChecker
from app.models.storefront import Storefront
from app.models.storefront_coupon import StorefrontCoupon
from app.models.user import User
from app.schemas import storefront_coupon as schemas

router = APIRouter()


def _validate_coupon_values(
    *,
    discount_type: str,
    value: float,
    starts_at: datetime | None,
    ends_at: datetime | None,
) -> None:
    normalized_type = discount_type.strip().upper()
    if normalized_type not in {"PERCENT", "FIXED"}:
        raise HTTPException(status_code=400, detail="El tipo de descuento debe ser PERCENT o FIXED")
    if normalized_type == "PERCENT" and value > 100:
        raise HTTPException(status_code=400, detail="El descuento porcentual no puede superar 100")
    if starts_at and ends_at and starts_at > ends_at:
        raise HTTPException(status_code=400, detail="La fecha inicial no puede ser posterior a la fecha final")


async def _get_company_storefront(
    db: AsyncSession,
    *,
    storefront_id,
    company_id,
) -> Storefront:
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


@router.get("/", response_model=List[schemas.CouponOut])
async def list_coupons(
    storefront_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
):
    query = select(StorefrontCoupon).where(
        StorefrontCoupon.company_id == current_user.company_id,
        StorefrontCoupon.is_active.is_(True),
    )
    if storefront_id:
        query = query.where(StorefrontCoupon.storefront_id == storefront_id)
    return (await db.execute(query.order_by(StorefrontCoupon.created_at.desc()))).scalars().all()


@router.post("/", response_model=schemas.CouponOut)
async def create_coupon(
    data: schemas.CouponIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
):
    await _get_company_storefront(
        db,
        storefront_id=data.storefront_id,
        company_id=current_user.company_id,
    )
    code = data.code.strip().upper()
    _validate_coupon_values(
        discount_type=data.discount_type,
        value=data.value,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
    )
    if await db.scalar(
        select(StorefrontCoupon.id).where(
            StorefrontCoupon.storefront_id == data.storefront_id,
            StorefrontCoupon.code == code,
            StorefrontCoupon.is_active.is_(True),
        )
    ):
        raise HTTPException(status_code=409, detail="El cupón ya existe")

    coupon = StorefrontCoupon(
        **data.model_dump(exclude={"code", "discount_type"}),
        code=code,
        discount_type=data.discount_type.strip().upper(),
        company_id=current_user.company_id,
        created_by_id=current_user.id,
    )
    db.add(coupon)
    await db.flush()
    await log_activity(
        db,
        action="CREATE",
        entity_type="StorefrontCoupon",
        entity_id=coupon.id,
        user_id=current_user.id,
        company_id=current_user.company_id,
        details={"code": coupon.code, "storefront_id": str(coupon.storefront_id)},
    )
    await db.commit()
    await db.refresh(coupon)
    return coupon


@router.put("/{coupon_id}", response_model=schemas.CouponOut)
async def update_coupon(
    coupon_id: str,
    data: schemas.CouponUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
):
    coupon = await db.scalar(
        select(StorefrontCoupon).where(
            StorefrontCoupon.id == coupon_id,
            StorefrontCoupon.company_id == current_user.company_id,
            StorefrontCoupon.is_active.is_(True),
        )
    )
    if not coupon:
        raise HTTPException(status_code=404, detail="Cupón no encontrado")

    values = data.model_dump(exclude_unset=True)
    storefront_id = values.get("storefront_id", coupon.storefront_id)
    if "storefront_id" in values:
        await _get_company_storefront(
            db,
            storefront_id=storefront_id,
            company_id=current_user.company_id,
        )
    code = str(values.get("code", coupon.code)).strip().upper()
    discount_type = str(values.get("discount_type", coupon.discount_type)).strip().upper()
    value = float(values.get("value", coupon.value))
    starts_at = values.get("starts_at", coupon.starts_at)
    ends_at = values.get("ends_at", coupon.ends_at)
    _validate_coupon_values(
        discount_type=discount_type,
        value=value,
        starts_at=starts_at,
        ends_at=ends_at,
    )
    if await db.scalar(
        select(StorefrontCoupon.id).where(
            StorefrontCoupon.storefront_id == storefront_id,
            StorefrontCoupon.code == code,
            StorefrontCoupon.id != coupon.id,
            StorefrontCoupon.is_active.is_(True),
        )
    ):
        raise HTTPException(status_code=409, detail="El cupón ya existe")

    for field, field_value in values.items():
        setattr(coupon, field, field_value)
    coupon.code = code
    coupon.discount_type = discount_type
    coupon.updated_by_id = current_user.id
    await log_activity(
        db,
        action="UPDATE",
        entity_type="StorefrontCoupon",
        entity_id=coupon.id,
        user_id=current_user.id,
        company_id=current_user.company_id,
        details={"code": coupon.code, "fields": list(values)},
    )
    await db.commit()
    await db.refresh(coupon)
    return coupon


@router.delete("/{coupon_id}", response_model=schemas.CouponOut)
async def disable_coupon(
    coupon_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
):
    coupon = await db.scalar(
        select(StorefrontCoupon).where(
            StorefrontCoupon.id == coupon_id,
            StorefrontCoupon.company_id == current_user.company_id,
            StorefrontCoupon.is_active.is_(True),
        )
    )
    if not coupon:
        raise HTTPException(status_code=404, detail="Cupón no encontrado")
    coupon.is_enabled = False
    coupon.updated_by_id = current_user.id
    await log_activity(
        db,
        action="DISABLE",
        entity_type="StorefrontCoupon",
        entity_id=coupon.id,
        user_id=current_user.id,
        company_id=current_user.company_id,
        details={"code": coupon.code},
    )
    await db.commit()
    await db.refresh(coupon)
    return coupon
