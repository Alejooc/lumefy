from typing import List
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.permissions import PermissionChecker
from app.models.storefront import Storefront
from app.models.storefront_coupon import StorefrontCoupon
from app.models.user import User
from app.schemas import storefront_coupon as schemas
router=APIRouter()
@router.get('/',response_model=List[schemas.CouponOut])
async def list_coupons(storefront_id:str|None=None,db:AsyncSession=Depends(get_db),current_user:User=Depends(PermissionChecker('manage_company'))):
 q=select(StorefrontCoupon).where(StorefrontCoupon.company_id==current_user.company_id,StorefrontCoupon.is_active==True)
 if storefront_id:q=q.where(StorefrontCoupon.storefront_id==storefront_id)
 return (await db.execute(q.order_by(StorefrontCoupon.created_at.desc()))).scalars().all()
@router.post('/',response_model=schemas.CouponOut)
async def create_coupon(data:schemas.CouponIn,db:AsyncSession=Depends(get_db),current_user:User=Depends(PermissionChecker('manage_company'))):
 if data.discount_type not in {'PERCENT','FIXED'} or(data.discount_type=='PERCENT' and data.value>100):raise HTTPException(400,'Cupón inválido')
 if not await db.scalar(select(Storefront.id).where(Storefront.id==data.storefront_id,Storefront.company_id==current_user.company_id)):raise HTTPException(404,'Tienda no encontrada')
 code=data.code.strip().upper()
 if await db.scalar(select(StorefrontCoupon.id).where(StorefrontCoupon.storefront_id==data.storefront_id,StorefrontCoupon.code==code,StorefrontCoupon.is_active==True)):raise HTTPException(409,'El cupón ya existe')
 coupon=StorefrontCoupon(**data.model_dump(exclude={'code'}),code=code,company_id=current_user.company_id,created_by_id=current_user.id);db.add(coupon);await db.commit();await db.refresh(coupon);return coupon
