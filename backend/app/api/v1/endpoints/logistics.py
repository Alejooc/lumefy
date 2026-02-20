from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.logistics import PackageType, SalePackage, SalePackageItem
from app.models.sale import Sale, SaleItem
from app.models.user import User
from app.core.permissions import PermissionChecker
from app.schemas import logistics as schemas
import uuid

router = APIRouter()

# --- Package Types ---

@router.get("/package-types", response_model=List[schemas.PackageType])
async def read_package_types(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(PermissionChecker("view_sales")),
) -> Any:
    query = select(PackageType).where(
        PackageType.company_id == current_user.company_id
    ).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/package-types", response_model=schemas.PackageType)
async def create_package_type(
    *,
    db: AsyncSession = Depends(get_db),
    type_in: schemas.PackageTypeCreate,
    current_user: User = Depends(PermissionChecker("manage_sales")),
) -> Any:
    pkg_type = PackageType(**type_in.dict(), company_id=current_user.company_id)
    db.add(pkg_type)
    await db.commit()
    await db.refresh(pkg_type)
    return pkg_type

@router.put("/package-types/{id}", response_model=schemas.PackageType)
async def update_package_type(
    *,
    db: AsyncSession = Depends(get_db),
    id: uuid.UUID,
    type_in: schemas.PackageTypeCreate,
    current_user: User = Depends(PermissionChecker("manage_sales")),
) -> Any:
    result = await db.execute(select(PackageType).where(
        PackageType.id == id,
        PackageType.company_id == current_user.company_id
    ))
    pkg_type = result.scalars().first()
    if not pkg_type:
        raise HTTPException(status_code=404, detail="Package type not found")
    for field, value in type_in.dict().items():
        setattr(pkg_type, field, value)
    await db.commit()
    await db.refresh(pkg_type)
    return pkg_type

@router.delete("/package-types/{id}")
async def delete_package_type(
    *,
    db: AsyncSession = Depends(get_db),
    id: uuid.UUID,
    current_user: User = Depends(PermissionChecker("manage_sales")),
) -> Any:
    result = await db.execute(select(PackageType).where(
        PackageType.id == id,
        PackageType.company_id == current_user.company_id
    ))
    pkg_type = result.scalars().first()
    if not pkg_type:
        raise HTTPException(status_code=404, detail="Package type not found")
    await db.delete(pkg_type)
    await db.commit()
    return {"ok": True}

# --- Picking ---

@router.post("/picking/update-item", response_model=bool)
async def update_picking_item(
    *,
    db: AsyncSession = Depends(get_db),
    picking_in: schemas.PickingUpdate,
    current_user: User = Depends(PermissionChecker("manage_sales")),
) -> Any:
    """
    Update the quantity picked for a specific Sale Item.
    """
    result = await db.execute(select(SaleItem).where(SaleItem.id == picking_in.sale_item_id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    # Validation
    if picking_in.quantity_picked > item.quantity:
        raise HTTPException(status_code=400, detail="Picked quantity cannot exceed ordered quantity")
        
    item.quantity_picked = picking_in.quantity_picked
    await db.commit()
    return True

# --- Packing ---

@router.get("/packages/{sale_id}", response_model=List[schemas.SalePackage])
async def read_sale_packages(
    *,
    db: AsyncSession = Depends(get_db),
    sale_id: uuid.UUID,
    current_user: User = Depends(PermissionChecker("view_sales")),
) -> Any:
    query = select(SalePackage).options(
        selectinload(SalePackage.items).selectinload(SalePackageItem.sale_item),
        selectinload(SalePackage.package_type)
    ).where(SalePackage.sale_id == sale_id)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/packages", response_model=schemas.SalePackage)
async def create_package(
    *,
    db: AsyncSession = Depends(get_db),
    package_in: schemas.SalePackageCreate,
    current_user: User = Depends(PermissionChecker("manage_sales")),
) -> Any:
    # Validate Sale exists
    result = await db.execute(select(Sale).where(
        Sale.id == package_in.sale_id,
        Sale.company_id == current_user.company_id
    ))
    sale = result.scalars().first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
        
    package = SalePackage(
        sale_id=package_in.sale_id,
        package_type_id=package_in.package_type_id,
        tracking_number=package_in.tracking_number,
        weight=package_in.weight,
        shipping_label_url=package_in.shipping_label_url
    )
    db.add(package)
    await db.flush()
    
    # Add items if any
    for item_in in package_in.items:
        pkg_item = SalePackageItem(
            package_id=package.id,
            sale_item_id=item_in.sale_item_id,
            quantity=item_in.quantity
        )
        db.add(pkg_item)
        
    await db.commit()
    
    # Reload for response
    query = select(SalePackage).options(
        selectinload(SalePackage.items).selectinload(SalePackageItem.sale_item),
        selectinload(SalePackage.package_type)
    ).where(SalePackage.id == package.id)
    result = await db.execute(query)
    return result.scalars().first()


# --- Kanban Board ---

@router.get("/board")
async def get_logistics_board(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_sales")),
) -> Any:
    """
    Get sales grouped by fulfillment stage for the Kanban board.
    """
    from app.models.sale import SaleStatus
    from app.models.client import Client

    stages = [
        SaleStatus.CONFIRMED,
        SaleStatus.PICKING,
        SaleStatus.PACKING,
        SaleStatus.DISPATCHED,
    ]

    board = {}
    for stage in stages:
        query = select(Sale).options(
            selectinload(Sale.client),
            selectinload(Sale.branch),
            selectinload(Sale.items).selectinload(SaleItem.product),
        ).where(
            Sale.company_id == current_user.company_id,
            Sale.status == stage,
        ).order_by(Sale.created_at.asc())

        result = await db.execute(query)
        sales = result.scalars().all()

        board[stage.value] = [
            {
                "id": str(s.id),
                "short_id": str(s.id)[:8],
                "client_name": s.client.name if s.client else "Sin cliente",
                "branch_name": s.branch.name if s.branch else "",
                "total": float(s.total),
                "item_count": len(s.items),
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "shipping_address": s.shipping_address,
                "notes": s.notes
            }
            for s in sales
        ]

    return board


@router.post("/board/move")
async def move_sale_stage(
    *,
    db: AsyncSession = Depends(get_db),
    move_in: dict,
    current_user: User = Depends(PermissionChecker("manage_sales")),
) -> Any:
    """
    Move a sale to a different fulfillment stage.
    """
    from app.models.sale import SaleStatus

    sale_id = move_in.get("sale_id")
    new_status = move_in.get("status")

    if not sale_id or not new_status:
        raise HTTPException(status_code=400, detail="sale_id and status are required")

    try:
        target_status = SaleStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {new_status}")

    allowed = [SaleStatus.CONFIRMED, SaleStatus.PICKING, SaleStatus.PACKING,
               SaleStatus.DISPATCHED, SaleStatus.DELIVERED]
    if target_status not in allowed:
        raise HTTPException(status_code=400, detail="Cannot move to this status")

    result = await db.execute(
        select(Sale).where(
            Sale.id == sale_id,
            Sale.company_id == current_user.company_id
        )
    )
    sale = result.scalars().first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    sale.status = target_status
    await db.commit()

    return {"ok": True, "status": target_status.value}

