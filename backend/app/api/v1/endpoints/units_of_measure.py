from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.unit_of_measure import UnitOfMeasure
from app.models.product import Product
from app.models.user import User
from app.core.permissions import PermissionChecker
from app.core.audit import log_activity
from app.schemas import unit_of_measure as schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.UnitOfMeasure])
async def list_units(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_products")),
) -> Any:
    query = select(UnitOfMeasure).where(
        UnitOfMeasure.company_id == current_user.company_id,
        UnitOfMeasure.is_active == True
    )
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=schemas.UnitOfMeasure)
async def create_unit(
    *,
    db: AsyncSession = Depends(get_db),
    unit_in: schemas.UnitOfMeasureCreate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    unit = UnitOfMeasure(**unit_in.model_dump(), company_id=current_user.company_id)
    db.add(unit)
    await db.commit()
    await db.refresh(unit)
    
    await log_activity(db, action="CREATE", entity_type="UnitOfMeasure", entity_id=unit.id,
                       user_id=current_user.id, company_id=current_user.company_id,
                       details=unit_in.model_dump())
    return unit

@router.put("/{unit_id}", response_model=schemas.UnitOfMeasure)
async def update_unit(
    *,
    db: AsyncSession = Depends(get_db),
    unit_id: str,
    unit_in: schemas.UnitOfMeasureUpdate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    result = await db.execute(
        select(UnitOfMeasure).where(
            UnitOfMeasure.id == unit_id,
            UnitOfMeasure.company_id == current_user.company_id
        )
    )
    unit = result.scalars().first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unidad de medida no encontrada")
    
    update_data = unit_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(unit, field, value)
    
    await db.commit()
    await db.refresh(unit)
    
    await log_activity(db, action="UPDATE", entity_type="UnitOfMeasure", entity_id=unit.id,
                       user_id=current_user.id, company_id=current_user.company_id,
                       details=update_data)
    return unit

@router.delete("/{unit_id}")
async def delete_unit(
    *,
    db: AsyncSession = Depends(get_db),
    unit_id: str,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    result = await db.execute(
        select(UnitOfMeasure).where(
            UnitOfMeasure.id == unit_id,
            UnitOfMeasure.company_id == current_user.company_id
        )
    )
    unit = result.scalars().first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unidad de medida no encontrada")
    
    # Check if used by products
    products_result = await db.execute(
        select(Product).where(
            (Product.unit_of_measure_id == unit_id) | (Product.purchase_uom_id == unit_id)
        ).limit(1)
    )
    if products_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="No se puede eliminar: hay productos que usan esta unidad de medida")
    
    await db.delete(unit)
    await db.commit()
    
    await log_activity(db, action="DELETE", entity_type="UnitOfMeasure", entity_id=unit_id,
                       user_id=current_user.id, company_id=current_user.company_id)
    return {"ok": True}
