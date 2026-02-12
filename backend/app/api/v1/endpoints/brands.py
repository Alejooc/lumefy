from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.brand import Brand
from app.models.product import Product
from app.models.user import User
from app.core.permissions import PermissionChecker
from app.core.audit import log_activity
from app.schemas import brand as schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.Brand])
async def list_brands(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_products")),
) -> Any:
    query = select(Brand).where(
        Brand.company_id == current_user.company_id,
        Brand.is_active == True
    )
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=schemas.Brand)
async def create_brand(
    *,
    db: AsyncSession = Depends(get_db),
    brand_in: schemas.BrandCreate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    brand = Brand(**brand_in.model_dump(), company_id=current_user.company_id)
    db.add(brand)
    await db.commit()
    await db.refresh(brand)
    
    await log_activity(db, action="CREATE", entity_type="Brand", entity_id=brand.id,
                       user_id=current_user.id, company_id=current_user.company_id,
                       details=brand_in.model_dump())
    return brand

@router.put("/{brand_id}", response_model=schemas.Brand)
async def update_brand(
    *,
    db: AsyncSession = Depends(get_db),
    brand_id: str,
    brand_in: schemas.BrandUpdate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    result = await db.execute(
        select(Brand).where(
            Brand.id == brand_id,
            Brand.company_id == current_user.company_id
        )
    )
    brand = result.scalars().first()
    if not brand:
        raise HTTPException(status_code=404, detail="Marca no encontrada")
    
    update_data = brand_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(brand, field, value)
    
    await db.commit()
    await db.refresh(brand)
    
    await log_activity(db, action="UPDATE", entity_type="Brand", entity_id=brand.id,
                       user_id=current_user.id, company_id=current_user.company_id,
                       details=update_data)
    return brand

@router.delete("/{brand_id}")
async def delete_brand(
    *,
    db: AsyncSession = Depends(get_db),
    brand_id: str,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    result = await db.execute(
        select(Brand).where(
            Brand.id == brand_id,
            Brand.company_id == current_user.company_id
        )
    )
    brand = result.scalars().first()
    if not brand:
        raise HTTPException(status_code=404, detail="Marca no encontrada")
    
    # Check if used by products
    products_result = await db.execute(
        select(Product).where(Product.brand_id == brand_id).limit(1)
    )
    if products_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="No se puede eliminar: hay productos que usan esta marca")
    
    await db.delete(brand)
    await db.commit()
    
    await log_activity(db, action="DELETE", entity_type="Brand", entity_id=brand_id,
                       user_id=current_user.id, company_id=current_user.company_id)
    return {"ok": True}
