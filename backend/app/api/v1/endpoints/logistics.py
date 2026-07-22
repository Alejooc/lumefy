from typing import Any, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.logistics import PackageType, SalePackage, SalePackageItem
from app.models.fulfillment_task import FulfillmentTask
from app.models.warehouse import Warehouse
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.sale import Sale, SaleItem, SaleStatus
from app.models.user import User
from app.core.permissions import PermissionChecker
from app.services.inventory_consumption import consume_fifo_lots
from app.services.outbox import enqueue_outbox_event
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

def _fulfillment_task_payload(task: FulfillmentTask) -> dict:
    sale = task.sale
    return {
        "id": str(task.id), "sale_id": str(task.sale_id), "warehouse_id": str(task.warehouse_id) if task.warehouse_id else None,
        "warehouse_name": task.warehouse.name if task.warehouse else "Sin bodega",
        "status": task.status, "created_at": task.created_at.isoformat() if task.created_at else None,
        "sale": {
            "id": str(sale.id), "status": sale.status.value, "total": float(sale.total),
            "client_name": sale.client.name if sale.client else "Cliente ocasional",
            "item_count": len(sale.items),
        },
    }


@router.get("/fulfillment-tasks")
async def read_fulfillment_tasks(
    warehouse_id: uuid.UUID | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_sales")),
) -> Any:
    query = select(FulfillmentTask).join(Sale).options(
        selectinload(FulfillmentTask.warehouse),
        selectinload(FulfillmentTask.sale).selectinload(Sale.client),
        selectinload(FulfillmentTask.sale).selectinload(Sale.items),
    ).where(FulfillmentTask.company_id == current_user.company_id)
    if warehouse_id:
        query = query.where(FulfillmentTask.warehouse_id == warehouse_id)
    if status:
        query = query.where(FulfillmentTask.status == status.upper())
    result = await db.execute(query.order_by(FulfillmentTask.created_at.asc()))
    return [_fulfillment_task_payload(task) for task in result.scalars().all()]


@router.post("/fulfillment-tasks/{task_id}/start")
async def start_fulfillment_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_sales")),
) -> Any:
    task = await db.scalar(select(FulfillmentTask).join(Sale).where(
        FulfillmentTask.id == task_id, FulfillmentTask.company_id == current_user.company_id,
    ).with_for_update())
    if not task:
        raise HTTPException(status_code=404, detail="Tarea de picking no encontrada")
    if task.status != "OPEN":
        raise HTTPException(status_code=400, detail="La tarea no está disponible para iniciar")
    sale = await db.scalar(select(Sale).where(Sale.id == task.sale_id).with_for_update())
    if not sale or sale.status != SaleStatus.CONFIRMED:
        raise HTTPException(status_code=400, detail="La orden ya no está disponible para picking")
    task.status = "IN_PROGRESS"
    sale.status = SaleStatus.PICKING
    await db.commit()
    return {"ok": True, "task_status": task.status, "sale_status": sale.status.value}


@router.post("/fulfillment-tasks/{task_id}/complete")
async def complete_fulfillment_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_sales")),
) -> Any:
    task = await db.scalar(select(FulfillmentTask).join(Sale).options(
        selectinload(FulfillmentTask.sale).selectinload(Sale.items).selectinload(SaleItem.product)
    ).where(FulfillmentTask.id == task_id, FulfillmentTask.company_id == current_user.company_id).with_for_update())
    if not task:
        raise HTTPException(status_code=404, detail="Tarea de picking no encontrada")
    sale = task.sale
    if task.status != "IN_PROGRESS" or sale.status != SaleStatus.PICKING:
        raise HTTPException(status_code=400, detail="La tarea no está en proceso de picking")
    physical_items = [item for item in sale.items if not item.product or item.product.product_type != "SERVICE"]
    if any(item.quantity_picked < item.quantity for item in physical_items):
        raise HTTPException(status_code=400, detail="Registra todas las unidades preparadas antes de finalizar")
    task.status = "COMPLETED"
    sale.status = SaleStatus.PACKING
    await db.commit()
    return {"ok": True, "task_status": task.status, "sale_status": sale.status.value}

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
    result = await db.execute(
        select(SaleItem)
        .join(Sale)
        .options(selectinload(SaleItem.sale))
        .where(
            SaleItem.id == picking_in.sale_item_id,
            Sale.company_id == current_user.company_id,
        )
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item.sale.status != SaleStatus.PICKING:
        raise HTTPException(status_code=400, detail="Solo se puede preparar un pedido en estado PICKING")
    if picking_in.quantity_picked < 0 or picking_in.quantity_picked > item.quantity:
        raise HTTPException(status_code=400, detail="La cantidad preparada debe estar entre 0 y la cantidad solicitada")
        
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
    query = select(SalePackage).join(Sale).options(
        selectinload(SalePackage.items).selectinload(SalePackageItem.sale_item),
        selectinload(SalePackage.package_type)
    ).where(
        SalePackage.sale_id == sale_id,
        Sale.company_id == current_user.company_id,
    )
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

    if sale.status != SaleStatus.PACKING:
        raise HTTPException(status_code=400, detail="Solo se puede empacar un pedido en estado PACKING")

    if package_in.package_type_id:
        package_type_result = await db.execute(select(PackageType).where(
            PackageType.id == package_in.package_type_id,
            PackageType.company_id == current_user.company_id,
        ))
        if not package_type_result.scalars().first():
            raise HTTPException(status_code=404, detail="Package type not found")

    if not package_in.items:
        raise HTTPException(status_code=400, detail="Agrega al menos un artículo al paquete")

    requested_items = {}
    for item in package_in.items:
        if item.quantity <= 0:
            raise HTTPException(status_code=400, detail="La cantidad empacada debe ser mayor a cero")
        requested_items[item.sale_item_id] = requested_items.get(item.sale_item_id, 0) + item.quantity

    if any(quantity <= 0 for quantity in requested_items.values()):
        raise HTTPException(status_code=400, detail="La cantidad empacada debe ser mayor a cero")

    sale_items_result = await db.execute(select(SaleItem).where(SaleItem.sale_id == sale.id))
    sale_items = {item.id: item for item in sale_items_result.scalars().all()}
    packed_result = await db.execute(
        select(
            SalePackageItem.sale_item_id,
            func.coalesce(func.sum(SalePackageItem.quantity), 0),
        )
        .join(SalePackage, SalePackage.id == SalePackageItem.package_id)
        .where(
            SalePackage.sale_id == sale.id,
            SalePackageItem.sale_item_id.in_(requested_items.keys()),
        )
        .group_by(SalePackageItem.sale_item_id)
    )
    already_packed = {sale_item_id: quantity for sale_item_id, quantity in packed_result.all()}

    for sale_item_id, quantity in requested_items.items():
        sale_item = sale_items.get(sale_item_id)
        if not sale_item:
            raise HTTPException(status_code=400, detail="Un artículo no pertenece a este pedido")
        if quantity > sale_item.quantity_picked:
            raise HTTPException(status_code=400, detail="No puedes empacar más unidades de las que fueron preparadas")
        if float(already_packed.get(sale_item_id, 0)) + quantity > sale_item.quantity_picked:
            raise HTTPException(status_code=400, detail="La cantidad ya empacada supera las unidades preparadas")
        
    package = SalePackage(
        sale_id=package_in.sale_id,
        package_type_id=package_in.package_type_id,
        tracking_number=package_in.tracking_number,
        carrier=package_in.carrier,
        service_level=package_in.service_level,
        weight=package_in.weight,
        shipping_label_url=package_in.shipping_label_url,
        company_id=current_user.company_id,
    )
    db.add(package)
    await db.flush()
    
    # Add items if any
    for sale_item_id, quantity in requested_items.items():
        pkg_item = SalePackageItem(
            package_id=package.id,
            sale_item_id=sale_item_id,
            quantity=quantity,
            company_id=current_user.company_id,
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
            selectinload(Sale.warehouse),
            selectinload(Sale.storefront_order),
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
                "warehouse_id": str(s.warehouse_id) if s.warehouse_id else None,
                "warehouse_name": s.warehouse.name if s.warehouse else "Sin bodega",
                "total": float(s.total),
                "item_count": len(s.items),
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "shipping_address": s.shipping_address,
                "notes": s.notes,
                "age_hours": round((datetime.now(timezone.utc) - s.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600, 1) if s.created_at else 0,
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

    result = await db.execute(
        select(Sale).options(
            selectinload(Sale.items).selectinload(SaleItem.product),
        ).where(
            Sale.id == sale_id,
            Sale.company_id == current_user.company_id
        )
    )
    sale = result.scalars().first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    valid_transitions = {
        SaleStatus.CONFIRMED: SaleStatus.PICKING,
        SaleStatus.PICKING: SaleStatus.PACKING,
        SaleStatus.PACKING: SaleStatus.DISPATCHED,
        SaleStatus.DISPATCHED: SaleStatus.DELIVERED,
    }
    expected_status = valid_transitions.get(sale.status)
    if target_status != expected_status:
        raise HTTPException(
            status_code=400,
            detail=f"Transición no permitida: {sale.status.value} a {target_status.value}",
        )

    physical_items = [
        item for item in sale.items
        if not item.product or item.product.product_type != "SERVICE"
    ]
    if target_status == SaleStatus.PACKING:
        if any(item.quantity_picked < item.quantity for item in physical_items):
            raise HTTPException(
                status_code=400,
                detail="Finaliza el picking de todas las unidades antes de pasar a empaque",
            )
    if target_status == SaleStatus.DISPATCHED:
        packed_result = await db.execute(
            select(
                SalePackageItem.sale_item_id,
                func.coalesce(func.sum(SalePackageItem.quantity), 0),
            )
            .join(SalePackage, SalePackage.id == SalePackageItem.package_id)
            .where(SalePackage.sale_id == sale.id)
            .group_by(SalePackageItem.sale_item_id)
        )
        packed_by_item = {sale_item_id: quantity for sale_item_id, quantity in packed_result.all()}
        if any(float(packed_by_item.get(item.id, 0)) < item.quantity for item in physical_items):
            raise HTTPException(
                status_code=400,
                detail="Empaca todas las unidades antes de despachar la orden",
            )
        packages_result = await db.execute(select(SalePackage).where(SalePackage.sale_id == sale.id))
        packages = packages_result.scalars().all()
        if sale.shipping_address and (not packages or any(not package.tracking_number for package in packages)):
            raise HTTPException(
                status_code=400,
                detail="Registra una transportadora y número de guía en cada paquete antes de despachar",
            )
        for item in sale.items:
            if not item.product or not item.product.track_inventory:
                continue
            inv_result = await db.execute(select(Inventory).where(
                Inventory.product_id == item.product_id,
                Inventory.branch_id == sale.branch_id,
                Inventory.warehouse_id == sale.warehouse_id,
            ))
            inventory = inv_result.scalars().first()
            if not inventory or inventory.reserved_quantity < item.quantity or inventory.quantity < item.quantity:
                raise HTTPException(status_code=400, detail=f"La reserva de '{item.product.name}' no está disponible para despachar")
            previous_stock = inventory.quantity
            inventory.reserved_quantity -= item.quantity
            inventory.quantity -= item.quantity
            fifo_unit_cost = await consume_fifo_lots(
                db,
                product=item.product,
                branch_id=sale.branch_id,
                company_id=current_user.company_id,
                quantity=item.quantity,
            )
            db.add(InventoryMovement(
                product_id=item.product_id,
                branch_id=sale.branch_id,
                warehouse_id=sale.warehouse_id,
                user_id=current_user.id,
                type=MovementType.OUT,
                quantity=-item.quantity,
                previous_stock=previous_stock,
                new_stock=inventory.quantity,
                unit_cost=fifo_unit_cost if fifo_unit_cost is not None else inventory.average_cost,
                reference_id=str(sale.id),
                reason="Sale Order Dispatched",
                company_id=current_user.company_id,
            ))

    sale.status = target_status
    if target_status == SaleStatus.PICKING:
        task = await db.scalar(select(FulfillmentTask).where(
            FulfillmentTask.sale_id == sale.id,
            FulfillmentTask.task_type == "PICKING",
        ))
        if task:
            task.status = "IN_PROGRESS"
    elif target_status == SaleStatus.PACKING:
        task = await db.scalar(select(FulfillmentTask).where(
            FulfillmentTask.sale_id == sale.id,
            FulfillmentTask.task_type == "PICKING",
        ))
        if task:
            task.status = "COMPLETED"
    elif target_status == SaleStatus.DISPATCHED:
        enqueue_outbox_event(
            db,
            event_type="inventory.dispatched",
            aggregate_type="sale",
            aggregate_id=sale.id,
            company_id=current_user.company_id,
            payload={"sale_id": str(sale.id), "warehouse_id": str(sale.warehouse_id) if sale.warehouse_id else None, "source": "logistics"},
        )
    elif target_status == SaleStatus.DELIVERED:
        enqueue_outbox_event(
            db,
            event_type="order.delivered",
            aggregate_type="sale",
            aggregate_id=sale.id,
            company_id=current_user.company_id,
            payload={"sale_id": str(sale.id), "source": "logistics"},
        )
    await db.commit()

    return {"ok": True, "status": target_status.value}

