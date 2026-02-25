from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.return_order import ReturnOrder, ReturnOrderItem, ReturnStatus, ReturnType
from app.models.sale import Sale, SaleItem, SaleStatus
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.user import User
from app.models.product import Product
from app.models.client import Client
from app.models.account_ledger import AccountLedger, LedgerType, PartnerType
from app.core.permissions import PermissionChecker
from app.schemas import return_order as schemas
from datetime import datetime, timezone
import uuid

router = APIRouter()


def _return_options():
    """Common eager-loading options for return queries."""
    from sqlalchemy.orm import selectinload
    return [
        selectinload(ReturnOrder.items).selectinload(ReturnOrderItem.product).options(
            selectinload(Product.brand),
            selectinload(Product.unit_of_measure),
            selectinload(Product.purchase_uom),
            selectinload(Product.variants),
            selectinload(Product.images),
        ),
        selectinload(ReturnOrder.creator),
        selectinload(ReturnOrder.approver),
    ]


@router.get("", response_model=List[schemas.ReturnOrderResponse])
async def list_returns(
    db: AsyncSession = Depends(get_db),
    sale_id: str = None,
    status: str = None,
    current_user: User = Depends(PermissionChecker("view_sales")),
) -> Any:
    """List return orders for the company."""
    query = select(ReturnOrder).options(*_return_options()).where(
        ReturnOrder.company_id == current_user.company_id
    )
    if sale_id:
        query = query.where(ReturnOrder.sale_id == sale_id)
    if status:
        query = query.where(ReturnOrder.status == status)
    query = query.order_by(ReturnOrder.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{return_id}", response_model=schemas.ReturnOrderResponse)
async def get_return(
    return_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_sales")),
) -> Any:
    """Get a single return order."""
    result = await db.execute(
        select(ReturnOrder).options(*_return_options()).where(
            ReturnOrder.id == return_id,
            ReturnOrder.company_id == current_user.company_id,
        )
    )
    ret = result.scalars().first()
    if not ret:
        raise HTTPException(status_code=404, detail="Return order not found")
    return ret


@router.post("", response_model=schemas.ReturnOrderResponse)
async def create_return(
    *,
    db: AsyncSession = Depends(get_db),
    return_in: schemas.ReturnOrderCreate,
    current_user: User = Depends(PermissionChecker("manage_sales")),
) -> Any:
    """Create a return order from a sale."""
    try:
        # Validate sale exists and is in valid state
        sale_result = await db.execute(
            select(Sale).options(selectinload(Sale.items)).where(
                Sale.id == return_in.sale_id,
                Sale.company_id == current_user.company_id,
            )
        )
        sale = sale_result.scalars().first()
        if not sale:
            raise HTTPException(status_code=404, detail="Sale not found")
        
        if sale.status not in (SaleStatus.DELIVERED, SaleStatus.COMPLETED):
            raise HTTPException(
                status_code=400,
                detail=f"Returns can only be created for DELIVERED or COMPLETED sales. Current: {sale.status.value}"
            )

        # Build item lookup
        sale_items_map = {str(si.id): si for si in sale.items}
        
        total_refund = 0.0
        return_items = []
        all_items_full = True
        
        for item_in in return_in.items:
            sale_item = sale_items_map.get(str(item_in.sale_item_id))
            if not sale_item:
                raise HTTPException(status_code=400, detail=f"Sale item {item_in.sale_item_id} not found in sale")
            
            if item_in.quantity <= 0:
                raise HTTPException(status_code=400, detail="Return quantity must be greater than 0")
            if item_in.quantity > sale_item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Return quantity ({item_in.quantity}) exceeds sold quantity ({sale_item.quantity}) for {sale_item.product_id}"
                )
            
            if item_in.quantity < sale_item.quantity:
                all_items_full = False
            
            subtotal = item_in.quantity * sale_item.price
            total_refund += subtotal
            
            return_items.append(ReturnOrderItem(
                sale_item_id=item_in.sale_item_id,
                product_id=sale_item.product_id,
                quantity_returned=item_in.quantity,
                unit_price=sale_item.price,
                subtotal=subtotal,
                company_id=current_user.company_id,
            ))
        
        # Determine if partial or total
        is_total = all_items_full and len(return_in.items) == len(sale.items)
        
        return_order = ReturnOrder(
            sale_id=return_in.sale_id,
            created_by=current_user.id,
            return_type=ReturnType.TOTAL if is_total else ReturnType.PARTIAL,
            status=ReturnStatus.PENDING,
            reason=return_in.reason,
            notes=return_in.notes,
            total_refund=total_refund,
            company_id=current_user.company_id,
        )
        return_order.items = return_items
        
        db.add(return_order)
        await db.commit()
        await db.refresh(return_order)
        
        # Re-fetch with eager loading
        result = await db.execute(
            select(ReturnOrder).options(*_return_options()).where(ReturnOrder.id == return_order.id)
        )
        return result.scalars().first()
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{return_id}/approve", response_model=schemas.ReturnOrderResponse)
async def approve_return(
    return_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_sales")),
) -> Any:
    """Approve a return, restore inventory and apply financial reversal when needed."""
    result = await db.execute(
        select(ReturnOrder).options(
            selectinload(ReturnOrder.items)
        ).where(
            ReturnOrder.id == return_id,
            ReturnOrder.company_id == current_user.company_id,
        )
    )
    ret = result.scalars().first()
    if not ret:
        raise HTTPException(status_code=404, detail="Return order not found")
    if ret.status != ReturnStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Return must be PENDING. Current: {ret.status.value}")
    
    # Get the sale to know which branch to restock
    sale_result = await db.execute(select(Sale).where(Sale.id == ret.sale_id))
    sale = sale_result.scalars().first()
    if not sale:
        raise HTTPException(status_code=404, detail="Related sale not found")
    
    # Restore inventory for each returned item
    for item in ret.items:
        # Get current inventory
        inv_result = await db.execute(
            select(Inventory).where(
                Inventory.product_id == item.product_id,
                Inventory.branch_id == sale.branch_id,
            )
        )
        inventory = inv_result.scalars().first()
        
        previous_stock = 0.0
        if inventory:
            previous_stock = inventory.quantity
        else:
            inventory = Inventory(
                product_id=item.product_id,
                branch_id=sale.branch_id,
                quantity=0.0,
                company_id=current_user.company_id,
            )
            db.add(inventory)
        
        new_stock = previous_stock + item.quantity_returned
        inventory.quantity = new_stock
        
        # Record movement
        movement = InventoryMovement(
            product_id=item.product_id,
            branch_id=sale.branch_id,
            user_id=current_user.id,
            type=MovementType.IN,
            quantity=item.quantity_returned,
            previous_stock=previous_stock,
            new_stock=new_stock,
            reason=f"Return approved: {ret.reason or 'N/A'}",
            reference_id=str(ret.id),
            company_id=current_user.company_id,
        )
        db.add(movement)

    # Financial reversal for credit sales: reduce customer's AR balance
    if sale.payment_method == "CREDIT" and sale.client_id:
        client_result = await db.execute(
            select(Client).where(
                Client.id == sale.client_id,
                Client.company_id == current_user.company_id
            )
        )
        client = client_result.scalars().first()
        if client:
            new_balance = client.current_balance - float(ret.total_refund or 0.0)
            client.current_balance = new_balance
            db.add(
                AccountLedger(
                    partner_id=client.id,
                    partner_type=PartnerType.CLIENT,
                    type=LedgerType.REFUND,
                    amount=float(ret.total_refund or 0.0),
                    balance_after=new_balance,
                    reference_id=str(ret.id),
                    description=f"Devolucion aprobada de venta {str(sale.id)[:8]}"
                )
            )
    
    ret.status = ReturnStatus.APPROVED
    ret.approved_at = datetime.now(timezone.utc)
    ret.approved_by = current_user.id
    
    await db.commit()
    
    # Re-fetch with eager loading
    result = await db.execute(
        select(ReturnOrder).options(*_return_options()).where(ReturnOrder.id == ret.id)
    )
    return result.scalars().first()


@router.post("/{return_id}/reject", response_model=schemas.ReturnOrderResponse)
async def reject_return(
    return_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_sales")),
) -> Any:
    """Reject a return order."""
    result = await db.execute(
        select(ReturnOrder).options(*_return_options()).where(
            ReturnOrder.id == return_id,
            ReturnOrder.company_id == current_user.company_id,
        )
    )
    ret = result.scalars().first()
    if not ret:
        raise HTTPException(status_code=404, detail="Return order not found")
    if ret.status != ReturnStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Return must be PENDING. Current: {ret.status.value}")
    
    ret.status = ReturnStatus.REJECTED
    await db.commit()
    await db.refresh(ret)
    return ret
