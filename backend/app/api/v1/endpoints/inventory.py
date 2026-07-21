from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from app.core.database import get_db
from app.models.inventory import Inventory
from app.models.inventory_lot import InventoryLot
from app.models.inventory_location import InventoryLocation
from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.branch import Branch
from app.models.warehouse import Warehouse
from app.models.user import User
from app.core import auth
from app.core.permissions import PermissionChecker
from app.schemas import inventory as schemas
import datetime

router = APIRouter()

from sqlalchemy.orm import selectinload

from app.models.product import Product


async def _validate_company_product_and_branch(
    db: AsyncSession,
    *,
    product_id: str,
    branch_id: str,
    company_id: str,
) -> None:
    product_result = await db.execute(
        select(Product.id).where(Product.id == product_id, Product.company_id == company_id)
    )
    if not product_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    branch_result = await db.execute(
        select(Branch.id).where(Branch.id == branch_id, Branch.company_id == company_id)
    )
    if not branch_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")

async def _validate_location(db: AsyncSession, branch_id: str, warehouse_id: str, location: str | None, company_id: str) -> None:
    if not location:
        return
    found = await db.scalar(select(InventoryLocation.id).where(
        InventoryLocation.branch_id == branch_id,
        InventoryLocation.warehouse_id == warehouse_id,
        InventoryLocation.code == location,
        InventoryLocation.company_id == company_id,
        InventoryLocation.is_active.is_(True),
    ))
    if not found:
        raise HTTPException(status_code=404, detail=f"Ubicación '{location}' no encontrada en la bodega")


async def _resolve_warehouse(db: AsyncSession, branch_id: str, warehouse_id: str | None, company_id: str) -> Warehouse:
    query = select(Warehouse).where(
        Warehouse.branch_id == branch_id,
        Warehouse.company_id == company_id,
        Warehouse.is_active.is_(True),
    )
    if warehouse_id:
        query = query.where(Warehouse.id == warehouse_id)
    else:
        query = query.where(Warehouse.is_default.is_(True))
    warehouse = await db.scalar(query)
    if not warehouse:
        raise HTTPException(status_code=404, detail="Bodega no encontrada para la sucursal")
    return warehouse

@router.get("/", response_model=List[schemas.Inventory])
async def read_inventory(
    db: AsyncSession = Depends(get_db),
    branch_id: str = None,
    warehouse_id: str = None,
    product_id: str = None,
    current_user: User = Depends(PermissionChecker("view_inventory")),
) -> Any:
    """
    Retrieve current stock. Use filters needed.
    """
    query = select(Inventory).options(
        selectinload(Inventory.product).options(
            selectinload(Product.images),
            selectinload(Product.variants),
            selectinload(Product.brand),
            selectinload(Product.unit_of_measure),
            selectinload(Product.purchase_uom),
            selectinload(Product.category)
        ),
        selectinload(Inventory.branch)
    ).join(Branch, Inventory.branch_id == Branch.id).where(
        Branch.company_id == current_user.company_id
    )
    
    if branch_id:
        query = query.where(Inventory.branch_id == branch_id)
    if warehouse_id:
        query = query.where(Inventory.warehouse_id == warehouse_id)
    if product_id:
        query = query.where(Inventory.product_id == product_id)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/export")
async def export_inventory(
    db: AsyncSession = Depends(get_db),
    format: str = "excel",
    branch_id: str = None,
    current_user: User = Depends(PermissionChecker("view_inventory")),
) -> Any:
    """Export inventory to Excel or CSV."""
    from app.services.export_service import ExportService

    query = select(Inventory).options(
        selectinload(Inventory.product),
        selectinload(Inventory.branch),
    ).join(Branch, Inventory.branch_id == Branch.id).where(
        Branch.company_id == current_user.company_id
    )
    if branch_id:
        query = query.where(Inventory.branch_id == branch_id)

    result = await db.execute(query)
    items = result.scalars().all()

    columns = {
        "product_name": "Producto",
        "product_sku": "SKU",
        "branch_name": "Sucursal",
        "quantity": "Cantidad",
        "min_quantity": "Stock Mínimo",
        "max_quantity": "Stock Máximo",
    }

    rows = []
    for inv in items:
        rows.append({
            "product_name": inv.product.name if inv.product else "",
            "product_sku": inv.product.sku if inv.product else "",
            "branch_name": inv.branch.name if inv.branch else "",
            "quantity": float(inv.quantity) if inv.quantity else 0,
            "min_quantity": float(inv.min_quantity) if getattr(inv, "min_quantity", None) else 0,
            "max_quantity": float(inv.max_quantity) if getattr(inv, "max_quantity", None) else 0,
        })

    if format == "csv":
        return ExportService.to_csv_response(rows, columns, filename="inventario")
    return ExportService.to_excel_response(rows, columns, filename="inventario")


@router.get("/replenishment")
async def get_replenishment_suggestions(
    db: AsyncSession = Depends(get_db),
    branch_id: str = None,
    current_user: User = Depends(PermissionChecker("view_inventory")),
) -> Any:
    """List tracked products that have reached their configured minimum stock."""
    query = (
        select(Product, Branch, func.coalesce(Inventory.quantity, 0.0))
        .select_from(Product)
        .join(Branch, Branch.company_id == Product.company_id)
        .outerjoin(
            Inventory,
            (Inventory.product_id == Product.id) & (Inventory.branch_id == Branch.id),
        )
        .where(
            Product.company_id == current_user.company_id,
            Product.track_inventory.is_(True),
            Product.min_stock > 0,
        )
        .order_by(Product.name, Branch.name)
    )
    if branch_id:
        query = query.where(Branch.id == branch_id)
    result = await db.execute(query)
    suggestions = []
    for product, branch, quantity in result.all():
        current_qty = float(quantity or 0)
        if current_qty > product.min_stock:
            continue
        target_qty = float(product.min_stock) * 2
        suggestions.append({
            "product_id": str(product.id),
            "product_name": product.name,
            "sku": product.sku,
            "branch_id": str(branch.id),
            "branch_name": branch.name,
            "current_quantity": current_qty,
            "minimum_quantity": float(product.min_stock),
            "suggested_quantity": max(float(product.min_stock) - current_qty, target_qty - current_qty),
        })
    return suggestions


@router.get("/valuation")
async def get_inventory_valuation(
    db: AsyncSession = Depends(get_db),
    branch_id: str = None,
    current_user: User = Depends(PermissionChecker("view_inventory")),
) -> Any:
    """Return inventory value by branch using the current weighted-average cost."""
    query = (
        select(
            Branch.id,
            Branch.name,
            func.coalesce(func.sum(Inventory.quantity * Inventory.average_cost), 0.0),
            func.coalesce(func.sum(Inventory.quantity), 0.0),
        )
        .select_from(Branch)
        .outerjoin(Inventory, Inventory.branch_id == Branch.id)
        .where(Branch.company_id == current_user.company_id)
        .group_by(Branch.id, Branch.name)
        .order_by(Branch.name)
    )
    if branch_id:
        query = query.where(Branch.id == branch_id)
    result = await db.execute(query)
    branches = [
        {
            "branch_id": str(id),
            "branch_name": name,
            "stock_quantity": float(quantity or 0),
            "inventory_value": float(value or 0),
        }
        for id, name, value, quantity in result.all()
    ]
    return {
        "branches": branches,
        "total_value": sum(branch["inventory_value"] for branch in branches),
    }


@router.get("/lots")
async def read_inventory_lots(
    db: AsyncSession = Depends(get_db),
    branch_id: str = None,
    product_id: str = None,
    current_user: User = Depends(PermissionChecker("view_inventory")),
) -> Any:
    """Traceable lot and serial balances, including expiry information."""
    query = select(InventoryLot).options(
        selectinload(InventoryLot.product),
        selectinload(InventoryLot.branch),
    ).join(Branch, InventoryLot.branch_id == Branch.id).where(
        InventoryLot.company_id == current_user.company_id,
        InventoryLot.quantity > 0,
    ).order_by(InventoryLot.expiry_date.asc().nullslast(), InventoryLot.created_at.asc())
    if branch_id:
        query = query.where(InventoryLot.branch_id == branch_id)
    if product_id:
        query = query.where(InventoryLot.product_id == product_id)
    result = await db.execute(query)
    return [
        {
            "id": str(lot.id),
            "product_id": str(lot.product_id),
            "product_name": lot.product.name if lot.product else "",
            "branch_id": str(lot.branch_id),
            "branch_name": lot.branch.name if lot.branch else "",
            "lot_number": lot.lot_number,
            "serial_number": lot.serial_number,
            "quantity": lot.quantity,
            "expiry_date": lot.expiry_date.isoformat() if lot.expiry_date else None,
            "unit_cost": lot.unit_cost,
            "source_reference": lot.source_reference,
        }
        for lot in result.scalars().all()
    ]

@router.post("/movement", response_model=schemas.Movement)
async def create_movement(
    *,
    db: AsyncSession = Depends(get_db),
    movement_in: schemas.MovementCreate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """
    Register a stock movement (IN/OUT/ADJ/TRF).
    Updates the Inventory table automatically.
    """
    await _validate_company_product_and_branch(
        db,
        product_id=str(movement_in.product_id),
        branch_id=str(movement_in.branch_id),
        company_id=str(current_user.company_id),
    )
    source_warehouse = await _resolve_warehouse(
        db,
        str(movement_in.branch_id),
        str(movement_in.warehouse_id) if movement_in.warehouse_id else None,
        str(current_user.company_id),
    )
    await _validate_location(db, str(movement_in.branch_id), str(source_warehouse.id), movement_in.location, str(current_user.company_id))

    if movement_in.quantity == 0:
        raise HTTPException(status_code=400, detail="La cantidad del movimiento debe ser distinta de cero")
    if movement_in.unit_cost is not None and movement_in.unit_cost < 0:
        raise HTTPException(status_code=400, detail="El costo unitario no puede ser negativo")

    product_result = await db.execute(
        select(Product).where(
            Product.id == movement_in.product_id,
            Product.company_id == current_user.company_id,
        )
    )
    product = product_result.scalars().first()
    
    # 1. Get current inventory record
    result = await db.execute(
        select(Inventory).where(
            Inventory.product_id == movement_in.product_id,
            Inventory.branch_id == movement_in.branch_id,
            Inventory.warehouse_id == source_warehouse.id,
        )
    )
    inventory_item = result.scalars().first()
    
    previous_stock = 0.0
    if inventory_item:
        previous_stock = inventory_item.quantity
    # 2. Calculate new stock
    change_qty = movement_in.quantity
    
    # Logic for signs:
    # Client serves 'quantity' as absolute value usually? 
    # Or signed? 
    # Standard: 
    # IN, ADJ (Postive) -> +
    # OUT -> -
    
    if movement_in.type == MovementType.TRF:
        # Transfer Logic
        if not movement_in.destination_branch_id:
             raise HTTPException(status_code=400, detail="Destination branch required for transfer")
        await _validate_company_product_and_branch(
            db,
            product_id=str(movement_in.product_id),
            branch_id=str(movement_in.destination_branch_id),
            company_id=str(current_user.company_id),
        )
        destination_warehouse = await _resolve_warehouse(
            db,
            str(movement_in.destination_branch_id),
            str(movement_in.destination_warehouse_id) if movement_in.destination_warehouse_id else None,
            str(current_user.company_id),
        )
        if destination_warehouse.id == source_warehouse.id:
            raise HTTPException(status_code=400, detail="La bodega origen y destino no pueden ser la misma")
        await _validate_location(db, str(movement_in.destination_branch_id), str(destination_warehouse.id), movement_in.destination_location, str(current_user.company_id))
             
        available = (inventory_item.quantity - inventory_item.reserved_quantity) if inventory_item else 0
        if available < abs(change_qty):
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente para transferir. Disponible: {available:g}",
            )

        # 1. OUT from Source
        # (inventory_item already fetched above)
        previous_stock_src = inventory_item.quantity
        final_change_src = -abs(change_qty)
        new_stock_src = previous_stock_src + final_change_src
        inventory_item.quantity = new_stock_src
        if movement_in.location:
            inventory_item.location = movement_in.location
        
        movement_src = InventoryMovement(
            product_id=movement_in.product_id,
            branch_id=movement_in.branch_id,
            warehouse_id=source_warehouse.id,
            user_id=current_user.id,
            type=MovementType.TRF,
            quantity=final_change_src, 
            previous_stock=previous_stock_src,
            new_stock=new_stock_src,
            reason=f"Transfer OUT to Branch {movement_in.destination_branch_id}",
            reference_id=movement_in.reference_id,
            company_id=current_user.company_id,
            unit_cost=inventory_item.average_cost,
        )
        db.add(movement_src)
        
        # 2. IN to Destination
        # Fetch Dest Inventory
        result_dest = await db.execute(
            select(Inventory).where(
                Inventory.product_id == movement_in.product_id,
                Inventory.branch_id == movement_in.destination_branch_id,
                Inventory.warehouse_id == destination_warehouse.id,
            )
        )
        inv_dest = result_dest.scalars().first()
        
        previous_stock_dest = 0.0
        if inv_dest:
            previous_stock_dest = inv_dest.quantity
        else:
            inv_dest = Inventory(
                product_id=movement_in.product_id,
                branch_id=movement_in.destination_branch_id,
                warehouse_id=destination_warehouse.id,
                quantity=0.0,
                average_cost=0.0,
                company_id=current_user.company_id,
            )
            db.add(inv_dest)
            
        final_change_dest = abs(change_qty)
        new_stock_dest = previous_stock_dest + final_change_dest
        inv_dest.quantity = new_stock_dest
        if movement_in.destination_location:
            inv_dest.location = movement_in.destination_location
        transferred_cost = inventory_item.average_cost
        if new_stock_dest > 0:
            inv_dest.average_cost = (
                (previous_stock_dest * inv_dest.average_cost) + (final_change_dest * transferred_cost)
            ) / new_stock_dest
        
        movement_dest = InventoryMovement(
            product_id=movement_in.product_id,
            branch_id=movement_in.destination_branch_id,
            warehouse_id=destination_warehouse.id,
            user_id=current_user.id,
            type=MovementType.TRF,
            quantity=final_change_dest,
            previous_stock=previous_stock_dest,
            new_stock=new_stock_dest,
            reason=f"Transfer IN from Branch {movement_in.branch_id}",
            reference_id=movement_in.reference_id,
            company_id=current_user.company_id,
            unit_cost=transferred_cost,
        )
        db.add(movement_dest)
        
        try:
            await db.commit()
            await db.refresh(movement_src)
            # Return source movement as main response
            movement = movement_src 
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    else:
        # Standard Logic (IN, OUT, ADJ)
        final_change = 0.0
        
        if movement_in.type == MovementType.IN:
            final_change = abs(change_qty)
        elif movement_in.type == MovementType.OUT:
            final_change = -abs(change_qty)
        elif movement_in.type == MovementType.ADJ:
            final_change = change_qty 
            
        new_stock = previous_stock + final_change

        reserved_quantity = inventory_item.reserved_quantity if inventory_item else 0.0
        if new_stock < reserved_quantity:
            raise HTTPException(
                status_code=400,
                detail=f"El movimiento usaría stock reservado. Disponible: {previous_stock - reserved_quantity:g}",
            )

        if not inventory_item:
            inventory_item = Inventory(
                product_id=movement_in.product_id,
                branch_id=movement_in.branch_id,
                warehouse_id=source_warehouse.id,
                quantity=0.0,
                average_cost=0.0,
                company_id=current_user.company_id,
            )
            db.add(inventory_item)
        
        movement_cost = inventory_item.average_cost
        if final_change > 0:
            movement_cost = movement_in.unit_cost if movement_in.unit_cost is not None else product.cost
            if new_stock > 0:
                inventory_item.average_cost = (
                    (previous_stock * inventory_item.average_cost) + (final_change * movement_cost)
                ) / new_stock

        # 3. Update Inventory
        inventory_item.quantity = new_stock
        if movement_in.location:
            inventory_item.location = movement_in.location
        
        # 4. Create Movement Record
        movement = InventoryMovement(
            product_id=movement_in.product_id,
            branch_id=movement_in.branch_id,
            warehouse_id=source_warehouse.id,
            user_id=current_user.id,
            type=movement_in.type,
            quantity=final_change, # Store the actual signed change
            previous_stock=previous_stock,
            new_stock=new_stock,
            reason=movement_in.reason,
            reference_id=movement_in.reference_id,
            company_id=current_user.company_id,
            unit_cost=movement_cost,
        )
        
        db.add(movement)
        
        try:
            await db.commit()
            await db.refresh(movement)
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
    
    # Eager load relationships for the response (Common)
    query = select(InventoryMovement).options(
        selectinload(InventoryMovement.product).options(
            selectinload(Product.images),
            selectinload(Product.variants),
            selectinload(Product.brand),
            selectinload(Product.unit_of_measure),
            selectinload(Product.purchase_uom),
            selectinload(Product.category)
        ),
        selectinload(InventoryMovement.branch),
        selectinload(InventoryMovement.user)
    ).where(InventoryMovement.id == movement.id)
    
    result = await db.execute(query)
    movement = result.scalars().first()
    
    return movement

@router.get("/movements", response_model=List[schemas.Movement])
async def read_movements(
    db: AsyncSession = Depends(get_db),
    product_id: str = None,
    branch_id: str = None,
    limit: int = 50,
    current_user: User = Depends(PermissionChecker("view_inventory")),
) -> Any:
    """
    Get movement history.
    """
    query = select(InventoryMovement).options(
        selectinload(InventoryMovement.product).options(
            selectinload(Product.images),
            selectinload(Product.variants),
            selectinload(Product.brand),
            selectinload(Product.unit_of_measure),
            selectinload(Product.purchase_uom),
            selectinload(Product.category)
        ),
        selectinload(InventoryMovement.branch),
        selectinload(InventoryMovement.user)

    ).join(Branch, InventoryMovement.branch_id == Branch.id).where(
        Branch.company_id == current_user.company_id
    ).order_by(InventoryMovement.created_at.desc()).limit(limit)
    
    if product_id:
        query = query.where(InventoryMovement.product_id == product_id)
    if branch_id:
        query = query.where(InventoryMovement.branch_id == branch_id)
        
    result = await db.execute(query)
    return result.scalars().all()
