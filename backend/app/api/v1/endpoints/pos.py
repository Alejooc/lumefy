from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.sale import Sale, SaleItem, Payment, SaleStatus
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.product import Product
from app.models.user import User
from app.core import auth
from app.core.permissions import PermissionChecker
from app.schemas import sale as schemas

import uuid

router = APIRouter()

@router.post("/", response_model=schemas.Sale)
async def create_sale(
    *,
    db: AsyncSession = Depends(get_db),
    sale_in: schemas.SaleCreate,
    current_user: User = Depends(PermissionChecker("pos_access")),
) -> Any:
    """
    Create a new POS sale.
    Handles: Sale creation, Items creation, Payment recording, Inventory deduction.
    """
    try:
        # 1. Create Sale Header
        sale = Sale(
            branch_id=sale_in.branch_id,
            user_id=current_user.id,
            client_id=sale_in.client_id,
            status=SaleStatus.COMPLETED, # Direct completion for POS
            payment_method=sale_in.payment_method, # Main method or mixed
            subtotal=0.0,
            tax=0.0,
            discount=0.0,
            total=0.0,
            company_id=current_user.company_id
        )
        db.add(sale)
        await db.flush() # Get ID
        
        total_amount = 0.0
        
        # 2. Process Items
        for item_in in sale_in.items:
            # Get Product to check price/stock (optional check)
            result = await db.execute(select(Product).where(Product.id == item_in.product_id))
            product = result.scalars().first()
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {item_in.product_id} not found")
            
            # Calculate total for item
            item_total = (item_in.price * item_in.quantity) - item_in.discount
            total_amount += item_total
            
            # Create SaleItem
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=item_in.product_id,
                quantity=item_in.quantity,
                price=item_in.price,
                discount=item_in.discount,
                total=item_total
            )
            db.add(sale_item)
            
            # 3. Update Inventory (Deduct Stock)
            if product.track_inventory:
                # Find current inventory
                inv_result = await db.execute(
                    select(Inventory).where(
                        Inventory.product_id == item_in.product_id,
                        Inventory.branch_id == sale_in.branch_id
                    )
                )
                inventory = inv_result.scalars().first()
                
                previous_stock = 0.0
                if inventory:
                    previous_stock = inventory.quantity
                else:
                     # Create if not exists (handling negative stock if allowed)
                    inventory = Inventory(
                        product_id=item_in.product_id,
                        branch_id=sale_in.branch_id,
                        quantity=0.0
                    )
                    db.add(inventory)
                
                new_stock = previous_stock - item_in.quantity
                inventory.quantity = new_stock
                
                # Record Movement
                movement = InventoryMovement(
                    product_id=item_in.product_id,
                    branch_id=sale_in.branch_id,
                    user_id=current_user.id,
                    type=MovementType.OUT,
                    quantity=-item_in.quantity,
                    previous_stock=previous_stock,
                    new_stock=new_stock,
                    reference_id=str(sale.id),
                    reason="POS Sale"
                )
                db.add(movement)

        # 4. Process Payments
        paid_amount = 0.0
        for pay_in in sale_in.payments:
            payment = Payment(
                sale_id=sale.id,
                method=pay_in.method,
                amount=pay_in.amount,
                reference=pay_in.reference
            )
            db.add(payment)
            paid_amount += pay_in.amount
            
        # 5. Finalize Sale
        sale.subtotal = total_amount # Simplified for now (tax calc logic to be added)
        sale.total = total_amount
        
        await db.commit()
        await db.refresh(sale)
        
        # Eager load for response
        query = select(Sale).options(
            selectinload(Sale.items).selectinload(SaleItem.product).options(
                selectinload(Product.brand),
                selectinload(Product.unit_of_measure),
                selectinload(Product.purchase_uom),
                selectinload(Product.variants),
                selectinload(Product.images)
            ),
            selectinload(Sale.payments),
            selectinload(Sale.user),
            selectinload(Sale.branch),
            selectinload(Sale.client)
        ).where(Sale.id == sale.id)
        
        result = await db.execute(query)
        return result.scalars().first()
        
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
