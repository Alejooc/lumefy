from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import PermissionChecker
from app.models.branch import Branch
from app.models.user import User
from app.models.warehouse import Warehouse
from app.schemas import warehouse as schemas

router = APIRouter()


async def _get_warehouse(db: AsyncSession, warehouse_id: UUID, company_id: UUID) -> Warehouse:
    warehouse = await db.scalar(select(Warehouse).join(Branch).where(
        Warehouse.id == warehouse_id, Warehouse.is_active.is_(True), Branch.company_id == company_id,
    ))
    if not warehouse:
        raise HTTPException(status_code=404, detail="Bodega no encontrada")
    return warehouse


@router.get("/", response_model=List[schemas.Warehouse])
async def list_warehouses(branch_id: UUID | None = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("view_inventory"))):
    query = select(Warehouse).join(Branch).where(Branch.company_id == current_user.company_id, Warehouse.is_active.is_(True))
    if branch_id:
        query = query.where(Warehouse.branch_id == branch_id)
    return (await db.execute(query.order_by(Warehouse.is_default.desc(), Warehouse.name))).scalars().all()


@router.post("/", response_model=schemas.Warehouse)
async def create_warehouse(data: schemas.WarehouseCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("manage_inventory"))):
    branch = await db.scalar(select(Branch).where(Branch.id == data.branch_id, Branch.company_id == current_user.company_id))
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    code = data.code.strip().upper()
    if await db.scalar(select(Warehouse.id).where(Warehouse.branch_id == branch.id, Warehouse.code == code, Warehouse.is_active.is_(True))):
        raise HTTPException(status_code=409, detail="El código de bodega ya existe en esta sucursal")
    if data.is_default:
        await db.execute(update(Warehouse).where(Warehouse.branch_id == branch.id).values(is_default=False))
    warehouse = Warehouse(**data.model_dump(exclude={"code"}), code=code, company_id=current_user.company_id, created_by_id=current_user.id, updated_by_id=current_user.id)
    db.add(warehouse)
    await db.commit()
    await db.refresh(warehouse)
    return warehouse


@router.put("/{warehouse_id}", response_model=schemas.Warehouse)
async def update_warehouse(warehouse_id: UUID, data: schemas.WarehouseUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("manage_inventory"))):
    warehouse = await _get_warehouse(db, warehouse_id, current_user.company_id)
    changes = data.model_dump(exclude_unset=True)
    if "code" in changes:
        changes["code"] = changes["code"].strip().upper()
    if changes.get("is_default"):
        await db.execute(update(Warehouse).where(Warehouse.branch_id == warehouse.branch_id, Warehouse.id != warehouse.id).values(is_default=False))
    for field, value in changes.items():
        setattr(warehouse, field, value)
    warehouse.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(warehouse)
    return warehouse
