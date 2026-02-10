from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import auth
from app.core.database import get_db
from app.models.purchase import PurchaseOrder, PurchaseStatus
from app.models.purchase_item import PurchaseOrderItem
from app.models.product import Product
from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.user import User
from app.core.permissions import PermissionChecker
from app.core.audit import log_activity
from app.schemas import purchase as schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.PurchaseOrder])
async def read_purchases(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(PermissionChecker("view_inventory")), 
) -> Any:
    """
    Retrieve purchase orders.
    """
    query = select(PurchaseOrder).where(
        PurchaseOrder.company_id == current_user.company_id
    ).options(selectinload(PurchaseOrder.items)).offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=schemas.PurchaseOrder)
async def create_purchase(
    *,
    db: AsyncSession = Depends(get_db),
    purchase_in: schemas.PurchaseOrderCreate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """
    Create Purchase Order.
    """
    # Create Header
    purchase = PurchaseOrder(
        supplier_id=purchase_in.supplier_id,
        branch_id=purchase_in.branch_id,
        notes=purchase_in.notes,
        expected_date=purchase_in.expected_date,
        user_id=current_user.id,
        company_id=current_user.company_id,
        status=PurchaseStatus.DRAFT,
        total_amount=0.0
    )
    db.add(purchase)
    await db.flush() # Get ID

    total = 0.0
    # Create Items
    for item_in in purchase_in.items:
        subtotal = item_in.quantity * item_in.unit_cost
        total += subtotal
        
        item = PurchaseOrderItem(
            purchase_id=purchase.id,
            product_id=item_in.product_id,
            quantity=item_in.quantity,
            unit_cost=item_in.unit_cost,
            subtotal=subtotal
        )
        db.add(item)
    
    purchase.total_amount = total
    await db.commit()
    
    # Reload with items
    query = select(PurchaseOrder).where(PurchaseOrder.id == purchase.id).options(selectinload(PurchaseOrder.items))
    result = await db.execute(query)
    purchase = result.scalars().first()
    
    await log_activity(db, "CREATE", "PurchaseOrder", purchase.id, current_user.id, current_user.company_id)
    return purchase

@router.put("/{purchase_id}/status", response_model=schemas.PurchaseOrder)
async def update_purchase_status(
    *,
    db: AsyncSession = Depends(get_db),
    purchase_id: UUID,
    status: PurchaseStatus,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """
    Update PO Status. Handling RECEIVED triggers inventory update.
    """
    query = select(PurchaseOrder).where(
        PurchaseOrder.id == purchase_id, 
        PurchaseOrder.company_id == current_user.company_id
    ).options(selectinload(PurchaseOrder.items))
    
    result = await db.execute(query)
    purchase = result.scalars().first()
    
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
        
    previous_status = purchase.status
    purchase.status = status
    
    # Logic for Receiving Stock
    if status == PurchaseStatus.RECEIVED and previous_status != PurchaseStatus.RECEIVED:
        if not purchase.branch_id:
             raise HTTPException(status_code=400, detail="Cannot receive without a destination Branch")
             
        for item in purchase.items:
            # 1. Update Product Stock (Global or ideally per branch, but we only have product.stock for now?)
            # Wait, InventoryMovement should handle stock calculation aggregation, BUT usually we verify against current stock.
            # Ideally Product model has a `stock` field which is a cached sum.
            
            # Fetch current product to update stock
            p_result = await db.execute(select(Product).where(Product.id == item.product_id))
            product = p_result.scalars().first()
            
            if product:
                original_stock = product.stock
                product.stock += item.quantity # Simple addition
                db.add(product)
                
                # 2. Create Movement
                movement = InventoryMovement(
                    product_id=item.product_id,
                    branch_id=purchase.branch_id,
                    user_id=current_user.id,
                    type=MovementType.IN,
                    quantity=item.quantity,
                    previous_stock=original_stock,
                    new_stock=product.stock,
                    reference_id=str(purchase.id),
                    reason="Purchase Received"
                )
                db.add(movement)
    
    await db.commit()
    await log_activity(db, "UPDATE_STATUS", "PurchaseOrder", purchase.id, current_user.id, current_user.company_id, {"status": status})
    return purchase
