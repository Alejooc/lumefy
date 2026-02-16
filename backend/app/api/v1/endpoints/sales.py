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

@router.get("/", response_model=List[schemas.SaleSummary])
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
    ).where(
        Sale.company_id == current_user.company_id
    ).offset(skip).limit(limit).order_by(Sale.created_at.desc())
         
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
        selectinload(Sale.items).selectinload(SaleItem.product).options(
            selectinload(Product.images),
            selectinload(Product.variants),
            selectinload(Product.brand),
            selectinload(Product.unit_of_measure),
            selectinload(Product.purchase_uom),
            selectinload(Product.category)
        ),
        selectinload(Sale.payments),
        selectinload(Sale.client),
        selectinload(Sale.user),
        selectinload(Sale.branch)
    ).where(
        Sale.id == id,
        Sale.company_id == current_user.company_id
    )
    
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
    try:
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
            total=0.0,
            company_id=current_user.company_id
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
        
        # --- Notification Trigger ---
        from app.models.notification import Notification
        from app.models.notification_template import NotificationTemplate
        from app.schemas.notification import NotificationType
        
        # 1. Get Template
        template_result = await db.execute(select(NotificationTemplate).where(NotificationTemplate.code == 'NEW_SALE'))
        template = template_result.scalars().first()
        
        if template and template.is_active:
            # 2. Notify all users in the company
            company_users_result = await db.execute(
                select(User).where(User.company_id == current_user.company_id)
            )
            company_users = company_users_result.scalars().all()
            
            # 3. Format Message
            title = template.title_template.format(order_id=str(sale.id)[:8])
            message = template.body_template.format(
                order_id=str(sale.id)[:8],
                amount=f"{sale.total:,.2f}",
                user_name=current_user.full_name or current_user.email
            )
            
            for user in company_users:
                notification = Notification(
                    user_id=user.id,
                    type=template.type, # Use template type
                    title=title,
                    message=message,
                    link=f"/admin/sales/view/{sale.id}"
                )
                db.add(notification)
            await db.commit()
        # ----------------------------
        
        # Eager load for response
        query = select(Sale).options(
            selectinload(Sale.items).selectinload(SaleItem.product).options(
                selectinload(Product.images),
                selectinload(Product.variants),
                selectinload(Product.brand),
                selectinload(Product.unit_of_measure),
                selectinload(Product.purchase_uom),
                selectinload(Product.category)
            ),
            selectinload(Sale.payments),
            selectinload(Sale.client),
            selectinload(Sale.user),
            selectinload(Sale.branch)
        ).where(Sale.id == sale.id)
        
        result = await db.execute(query)
        return result.scalars().first()

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

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
        selectinload(Sale.items).selectinload(SaleItem.product).options(
            selectinload(Product.images),
            selectinload(Product.variants),
            selectinload(Product.brand),
            selectinload(Product.unit_of_measure),
            selectinload(Product.purchase_uom),
            selectinload(Product.category)
        ),
        selectinload(Sale.payments),
        selectinload(Sale.client),
        selectinload(Sale.user),
        selectinload(Sale.branch)
    ).where(
        Sale.id == id,
        Sale.company_id == current_user.company_id
    )
    result = await db.execute(query)
    sale = result.scalars().first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
        
    old_status = sale.status
    new_status = status
    
    if old_status == new_status:
        return sale
        
    
    # LOGIC:
    # 1. DRAFT/QUOTE -> CONFIRMED (Deduct Inventory)
    # 2. CONFIRMED -> PICKING
    # 3. PICKING -> PACKING
    # 4. PACKING -> DISPATCHED
    # 5. DISPATCHED -> DELIVERED
    # 6. ANY -> CANCELLED (Restore Inventory if previously deducted)
    
    # Allow flow
    valid_transitions = {
        SaleStatus.DRAFT: [SaleStatus.CONFIRMED, SaleStatus.CANCELLED],
        SaleStatus.QUOTE: [SaleStatus.CONFIRMED, SaleStatus.CANCELLED],
        SaleStatus.CONFIRMED: [SaleStatus.PICKING, SaleStatus.PACKING, SaleStatus.DISPATCHED, SaleStatus.CANCELLED],
        SaleStatus.PICKING: [SaleStatus.PACKING, SaleStatus.DISPATCHED, SaleStatus.CANCELLED],
        SaleStatus.PACKING: [SaleStatus.DISPATCHED, SaleStatus.CANCELLED],
        SaleStatus.DISPATCHED: [SaleStatus.DELIVERED, SaleStatus.CANCELLED],
        SaleStatus.DELIVERED: [], # Final state
        SaleStatus.CANCELLED: [], # Final state (unless we allow re-drafting later)
    }
    
    # Bypass validation if we are just moving fast (optional), but let's enforce for now
    if new_status not in valid_transitions.get(old_status, []):
        # Allow skipping steps? E.g. CONFIRMED -> DISPATCHED directly
        # Let's allow forward movement skipping for flexibility
        pass 

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

                # --- Low Stock Warning ---
                if inventory.quantity <= item.product.min_stock:
                    # Notify All Users
                    # We need to query users if not already queried
                    # For efficiency, we might want to move this outside the loop or cache it, 
                    # but for now, query here is safer to ensure we get them.
                    # Or simpler: Query once before loop? No, loop might be empty.
                    # Let's query inside but it's N*M queries.  
                    # Optimization: Query all company users ONCE at start of this block.
                    
                    users_result = await db.execute(select(User).where(User.company_id == current_user.company_id))
                    users_list = users_result.scalars().all()

                    for user in users_list:
                        notif = Notification(
                            user_id=user.id,
                            type=NotificationType.WARNING,
                            title="⚠️ Stock Bajo",
                            message=f"El producto '{item.product.name}' ha llegado a su stock mínimo ({inventory.quantity} restantes).",
                            link=f"/admin/inventory"
                        )
                        db.add(notif)
                # -------------------------
                
    elif new_status == SaleStatus.CANCELLED and old_status in [SaleStatus.CONFIRMED, SaleStatus.PICKING, SaleStatus.PACKING, SaleStatus.DISPATCHED]:
        # Restore Inventory if it was deducted (CONFIRMED or later)
        # Note: If we move deduction to DISPATCHED, this needs change.
        # Current Logic: Deduction at CONFIRMED.
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
    
    # Reload with eager relationships for response
    query = select(Sale).options(
        selectinload(Sale.items).selectinload(SaleItem.product),
        selectinload(Sale.payments),
        selectinload(Sale.client),
        selectinload(Sale.user),
        selectinload(Sale.branch)
    ).where(Sale.id == id)
    
    result = await db.execute(query)
    sale = result.scalars().first()
    
    return sale

@router.delete("/{id}")
async def delete_sale(
    *,
    db: AsyncSession = Depends(get_db),
    id: uuid.UUID,
    current_user: User = Depends(PermissionChecker("manage_sales")),
) -> Any:
    """
    Delete a sale. Only DRAFT or QUOTE can be deleted.
    """
    query = select(Sale).options(
        selectinload(Sale.items),
        selectinload(Sale.payments),
    ).where(
        Sale.id == id,
        Sale.company_id == current_user.company_id
    )
    result = await db.execute(query)
    sale = result.scalars().first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    # Only allow deletion of drafts and quotes (Odoo-style)
    if sale.status not in [SaleStatus.DRAFT, SaleStatus.QUOTE]:
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden eliminar ventas en estado Borrador o Cotización"
        )
    
    # Delete items and payments
    for item in sale.items:
        await db.delete(item)
    for payment in sale.payments:
        await db.delete(payment)
    
    await db.delete(sale)
    await db.commit()
    return {"ok": True, "detail": "Venta eliminada"}


from fastapi.responses import StreamingResponse
from app.services.pdf_service import PDFService

@router.get("/{id}/pdf/{doc_type}")
async def download_pdf(
    *,
    db: AsyncSession = Depends(get_db),
    id: uuid.UUID,
    doc_type: str,
    current_user: User = Depends(PermissionChecker("view_sales")),
) -> Any:
    """
    Download PDF document (invoice, picking, packing).
    """
    if doc_type not in ["invoice", "picking", "packing"]:
        raise HTTPException(status_code=400, detail="Invalid document type")

    query = select(Sale).options(
        selectinload(Sale.items).selectinload(SaleItem.product).options(
            selectinload(Product.images),
            selectinload(Product.variants),
            selectinload(Product.brand),
            selectinload(Product.unit_of_measure),
            selectinload(Product.purchase_uom),
            selectinload(Product.category)
        ),
        selectinload(Sale.client),
        selectinload(Sale.user),
        selectinload(Sale.branch)
    ).where(
        Sale.id == id,
        Sale.company_id == current_user.company_id
    )
    result = await db.execute(query)
    sale = result.scalars().first()
    
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
        
    # Validation logic
    if doc_type == "picking" and sale.status not in [SaleStatus.CONFIRMED, SaleStatus.PICKING, SaleStatus.PACKING, SaleStatus.DISPATCHED]:
         raise HTTPException(status_code=400, detail="Picking list only available for Confirmed orders")
         
    if doc_type == "packing" and sale.status not in [SaleStatus.PACKING, SaleStatus.DISPATCHED, SaleStatus.DELIVERED]:
         raise HTTPException(status_code=400, detail="Packing list only available for Packed orders")

    from app.models.company import Company
    result = await db.execute(select(Company).where(Company.id == sale.company_id))
    company = result.scalars().first()

    service = PDFService()
    
    if doc_type == "invoice":
        buffer = service.generate_invoice(sale, company)
        filename = f"Factura_{str(sale.id)[:8]}.pdf"
    elif doc_type == "picking":
        buffer = service.generate_picking(sale, company)
        filename = f"Picking_{str(sale.id)[:8]}.pdf"
    elif doc_type == "packing":
        buffer = service.generate_packing(sale, company)
        filename = f"Packing_{str(sale.id)[:8]}.pdf"
        
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
