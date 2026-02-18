from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.branch import Branch
from app.models.user import User
from app.core import auth
from app.core.permissions import PermissionChecker
from app.schemas import inventory as schemas
import datetime

router = APIRouter()

from sqlalchemy.orm import selectinload

from app.models.product import Product

@router.get("/", response_model=List[schemas.Inventory])
async def read_inventory(
    db: AsyncSession = Depends(get_db),
    branch_id: str = None,
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
    
    # 1. Get current inventory record
    result = await db.execute(
        select(Inventory).where(
            Inventory.product_id == movement_in.product_id,
            Inventory.branch_id == movement_in.branch_id
        )
    )
    inventory_item = result.scalars().first()
    
    previous_stock = 0.0
    if inventory_item:
        previous_stock = inventory_item.quantity
    else:
        # Create new inventory record if not exists
        inventory_item = Inventory(
            product_id=movement_in.product_id,
            branch_id=movement_in.branch_id,
            quantity=0.0
        )
        db.add(inventory_item)
        
    # 2. Calculate new stock
    change_qty = movement_in.quantity
    
    # Logic for signs:
    # Client serves 'quantity' as absolute value usually? 
    # Or signed? 
    # Standard: 
    # IN, ADJ (Postive) -> +
    # OUT -> -
    
    final_change = 0.0
    
    if movement_in.type == MovementType.IN:
        final_change = abs(change_qty)
    elif movement_in.type == MovementType.OUT:
        final_change = -abs(change_qty)
    elif movement_in.type == MovementType.ADJ:
        final_change = change_qty # ADJ can be positive or negative
    elif movement_in.type == MovementType.TRF:
        final_change = -abs(change_qty) # Sender, need logic for Receiver? 
        # Transfer is complex, usually implies TWO movements. 
        # For now treat simple TRF as OUT from this branch.
        
    new_stock = previous_stock + final_change
    
    # 3. Update Inventory
    inventory_item.quantity = new_stock
    
    # 4. Create Movement Record
    movement = InventoryMovement(
        product_id=movement_in.product_id,
        branch_id=movement_in.branch_id,
        user_id=current_user.id,
        type=movement_in.type,
        quantity=final_change, # Store the actual signed change
        previous_stock=previous_stock,
        new_stock=new_stock,
        reason=movement_in.reason,
        reference_id=movement_in.reference_id
    )
    
    db.add(movement)
    
    try:
        await db.commit()
        await db.refresh(movement)
        # Eager load relationships for the response
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
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

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
