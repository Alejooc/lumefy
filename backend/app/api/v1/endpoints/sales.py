from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.sale import Sale, SaleItem, SaleStatus, Payment
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.product import Product
from app.models.user import User
from app.core.permissions import PermissionChecker
from app.schemas import sale as schemas
import uuid
from datetime import datetime

router = APIRouter()

@router.get("/", response_model=List[schemas.Sale])
async def read_sales(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    client_id: str = None,
    current_user: User = Depends(PermissionChecker("view_sales")),
) -> Any:
    """
    Retrieve sales orders.
    """
    query = select(Sale).options(
        selectinload(Sale.client),
        selectinload(Sale.user),
        selectinload(Sale.branch)
    ).offset(skip).limit(limit).order_by(Sale.created_at.desc())
    
    if current_user.company_id:
         # Need to join user to filter by company because Sale doesn't have company_id directly (it has user_id/branch_id)
         # However, correct way is to trust branch_id belongs to company or add company_id to Sale.
         # For now, let's assume filtering by branch logic or user.company linkage.
         # Actually Sale has branch_id, branch has company_id.
         pass # Pending strict multi-tenant filter implementation on Sale model directly
         
    if status:
        query = query.where(Sale.status == status)
    if client_id:
        query = query.where(Sale.client_id == uuid.UUID(client_id))
        
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{id}", response_model=schemas.Sale)
async def read_sale(
    *,
    db: AsyncSession = Depends(get_db),
    id: uuid.UUID,
    current_user: User = Depends(PermissionChecker("view_sales")),
) -> Any:
    """
    Get sale by ID.
    """
    query = select(Sale).options(
        selectinload(Sale.items).selectinload(SaleItem.product),
        selectinload(Sale.payments),
        selectinload(Sale.client),
        selectinload(Sale.user),
        selectinload(Sale.branch)
    ).where(Sale.id == id)
    
    result = await db.execute(query)
    sale = result.scalars().first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    return sale

@router.post("/", response_model=schemas.Sale)
async def create_sale(
    *,
    db: AsyncSession = Depends(get_db),
    sale_in: schemas.SaleCreate,
    current_user: User = Depends(PermissionChecker("create_sales")),
) -> Any:
    """
    Create a new Sale (Quote or Order).
    Does NOT affect inventory immediately unless status is CONFIRMED (which shouldn't be initial status usually).
    """
    # 1. Create Sale Header
    sale = Sale(
        branch_id=sale_in.branch_id,
        user_id=current_user.id,
        client_id=sale_in.client_id,
        status=sale_in.status if sale_in.status else SaleStatus.DRAFT,
        payment_method=sale_in.payment_method,
        notes=sale_in.notes,
        shipping_address=sale_in.shipping_address,
        valid_until=sale_in.valid_until,
        subtotal=0.0,
        tax=0.0,
        discount=0.0,
        total=0.0
    )
    db.add(sale)
    await db.flush()
    
    total_amount = 0.0
    
    # 2. Process Items
    for item_in in sale_in.items:
        # Get Product
        result = await db.execute(select(Product).where(Product.id == item_in.product_id))
        product = result.scalars().first()
        if not product:
            continue 
        
        item_total = (item_in.price * item_in.quantity) - item_in.discount
        total_amount += item_total
        
        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=item_in.product_id,
            quantity=item_in.quantity,
            price=item_in.price,
            discount=item_in.discount,
            total=item_total
        )
        db.add(sale_item)
        
    # 3. Finalize
    sale.subtotal = total_amount
    sale.total = total_amount # + tax + shipping
    
    await db.commit()
    await db.refresh(sale)
    return sale

@router.put("/{id}/status", response_model=schemas.Sale)
async def update_status(
    *,
    db: AsyncSession = Depends(get_db),
    id: uuid.UUID,
    status: str,
    current_user: User = Depends(PermissionChecker("manage_sales")),
) -> Any:
    """
    Update Sale status. Handles inventory logic.
    """
    query = select(Sale).options(
        selectinload(Sale.items).selectinload(SaleItem.product)
    ).where(Sale.id == id)
    result = await db.execute(query)
    sale = result.scalars().first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
        
    old_status = sale.status
    new_status = status
    
    if old_status == new_status:
        return sale
        
    # LOGIC:
    # If moving TO CONFIRMED -> Deduct Inventory
    # If moving FROM CONFIRMED/DISPATCHED TO CANCELLED -> Restore Inventory
    
    if new_status == SaleStatus.CONFIRMED and old_status in [SaleStatus.DRAFT, SaleStatus.QUOTE]:
        # Deduct Inventory
        for item in sale.items:
            if item.product and item.product.track_inventory:
                # Find Inventory
                inv_result = await db.execute(select(Inventory).where(
                    Inventory.product_id == item.product_id,
                    Inventory.branch_id == sale.branch_id
                ))
                inventory = inv_result.scalars().first()
                
                prev_stock = inventory.quantity if inventory else 0
                if inventory:
                    inventory.quantity -= item.quantity
                else:
                    inventory = Inventory(
                        product_id=item.product_id,
                        branch_id=sale.branch_id,
                        quantity=-item.quantity
                    )
                    db.add(inventory)
                
                # Log Movement
                movement = InventoryMovement(
                    product_id=item.product_id,
                    branch_id=sale.branch_id,
                    user_id=current_user.id,
                    type=MovementType.OUT,
                    quantity=-item.quantity,
                    previous_stock=prev_stock,
                    new_stock=inventory.quantity,
                    reference_id=str(sale.id),
                    reason="Sale Order Confirmed"
                )
                db.add(movement)
                
    elif new_status == SaleStatus.CANCELLED and old_status in [SaleStatus.CONFIRMED, SaleStatus.DISPATCHED]:
        # Restore Inventory
         for item in sale.items:
            if item.product and item.product.track_inventory:
                inv_result = await db.execute(select(Inventory).where(
                    Inventory.product_id == item.product_id,
                    Inventory.branch_id == sale.branch_id
                ))
                inventory = inv_result.scalars().first()
                
                prev_stock = inventory.quantity if inventory else 0
                if inventory:
                    inventory.quantity += item.quantity
                
                # Log Movement
                movement = InventoryMovement(
                    product_id=item.product_id,
                    branch_id=sale.branch_id,
                    user_id=current_user.id,
                    type=MovementType.IN,
                    quantity=item.quantity,
                    previous_stock=prev_stock,
                    new_stock=inventory.quantity,
                    reference_id=str(sale.id),
                    reason="Sale Order Cancelled"
                )
                db.add(movement)
    
    sale.status = new_status
    await db.commit()
    await db.refresh(sale)
    return sale
