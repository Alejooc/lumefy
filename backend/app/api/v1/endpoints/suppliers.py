from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import auth
from app.core.database import get_db
from app.models.supplier import Supplier
from app.models.user import User
from app.core.permissions import PermissionChecker
from app.core.audit import log_activity
from app.schemas import supplier as schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.Supplier])
async def read_suppliers(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(PermissionChecker("view_products")), # Using view_products for now
) -> Any:
    """
    Retrieve suppliers.
    """
    query = select(Supplier).where(Supplier.company_id == current_user.company_id).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=schemas.Supplier)
async def create_supplier(
    *,
    db: AsyncSession = Depends(get_db),
    supplier_in: schemas.SupplierCreate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """
    Create new supplier.
    """
    supplier = Supplier(**supplier_in.model_dump(), company_id=current_user.company_id)
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    
    await log_activity(db, "CREATE", "Supplier", supplier.id, current_user.id, current_user.company_id, supplier_in.model_dump())
    
    return supplier

@router.put("/{supplier_id}", response_model=schemas.Supplier)
async def update_supplier(
    *,
    db: AsyncSession = Depends(get_db),
    supplier_id: UUID,
    supplier_in: schemas.SupplierUpdate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """
    Update a supplier.
    """
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id, Supplier.company_id == current_user.company_id))
    supplier = result.scalars().first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
        
    update_data = supplier_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplier, field, value)
        
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    
    await log_activity(db, "UPDATE", "Supplier", supplier.id, current_user.id, current_user.company_id, update_data)
    
    return supplier

@router.delete("/{supplier_id}", response_model=schemas.Supplier)
async def delete_supplier(
    *,
    db: AsyncSession = Depends(get_db),
    supplier_id: UUID,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """
    Delete a supplier.
    """
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id, Supplier.company_id == current_user.company_id))
    supplier = result.scalars().first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
        
    await db.delete(supplier)
    await db.commit()
    
    await log_activity(db, "DELETE", "Supplier", supplier_id, current_user.id, current_user.company_id)
    
    return supplier
