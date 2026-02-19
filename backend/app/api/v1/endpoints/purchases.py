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
from app.models.inventory import Inventory
from app.models.user import User
from app.core.permissions import PermissionChecker
from app.core.audit import log_activity
from app.schemas import purchase as schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.PurchaseOrderSummary])
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
    ).options(
        selectinload(PurchaseOrder.supplier),
        selectinload(PurchaseOrder.branch)
    ).order_by(PurchaseOrder.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/export")
async def export_purchases(
    db: AsyncSession = Depends(get_db),
    format: str = "excel",
    current_user: User = Depends(PermissionChecker("view_inventory")),
) -> Any:
    """Export purchases to Excel or CSV."""
    from app.services.export_service import ExportService

    query = select(PurchaseOrder).options(
        selectinload(PurchaseOrder.supplier),
        selectinload(PurchaseOrder.branch),
    ).where(
        PurchaseOrder.company_id == current_user.company_id
    ).order_by(PurchaseOrder.created_at.desc())

    result = await db.execute(query)
    purchases = result.scalars().all()

    columns = {
        "order_number": "# Orden",
        "created_at": "Fecha",
        "supplier_name": "Proveedor",
        "branch_name": "Sucursal",
        "status": "Estado",
        "total": "Total",
    }

    rows = []
    for p in purchases:
        rows.append({
            "order_number": getattr(p, "order_number", "") or str(p.id)[:8],
            "created_at": p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "",
            "supplier_name": p.supplier.name if p.supplier else "",
            "branch_name": p.branch.name if p.branch else "",
            "status": p.status or "",
            "total": float(p.total) if p.total else 0,
        })

    if format == "csv":
        return ExportService.to_csv_response(rows, columns, filename="compras")
    return ExportService.to_excel_response(rows, columns, filename="compras")

@router.get("/{purchase_id}", response_model=schemas.PurchaseOrder)
async def read_purchase(
    *,
    db: AsyncSession = Depends(get_db),
    purchase_id: UUID,
    current_user: User = Depends(PermissionChecker("view_inventory")),
) -> Any:
    """
    Get purchase by ID.
    """
    query = select(PurchaseOrder).where(
        PurchaseOrder.id == purchase_id,
        PurchaseOrder.company_id == current_user.company_id
    ).options(
        selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product).options(
            selectinload(Product.images),
            selectinload(Product.variants),
            selectinload(Product.brand),
            selectinload(Product.unit_of_measure),
            selectinload(Product.purchase_uom),
            selectinload(Product.category)
        ),
        selectinload(PurchaseOrder.supplier),
        selectinload(PurchaseOrder.branch)
    )
    
    result = await db.execute(query)
    purchase = result.scalars().first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    return purchase

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
    try:
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
        query = select(PurchaseOrder).where(PurchaseOrder.id == purchase.id).options(
            selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product).options(
                selectinload(Product.images),
                selectinload(Product.variants),
                selectinload(Product.brand),
                selectinload(Product.unit_of_measure),
                selectinload(Product.purchase_uom),
                selectinload(Product.category)
            ),
            selectinload(PurchaseOrder.supplier),
            selectinload(PurchaseOrder.branch)
        )
        result = await db.execute(query)
        purchase = result.scalars().first()
        
        await log_activity(db, "CREATE", "PurchaseOrder", purchase.id, current_user.id, current_user.company_id)
        return purchase
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

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
    ).options(
        selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product).options(
            selectinload(Product.images),
            selectinload(Product.variants),
            selectinload(Product.brand),
            selectinload(Product.unit_of_measure),
            selectinload(Product.purchase_uom),
            selectinload(Product.category)
        ),
        selectinload(PurchaseOrder.supplier),
        selectinload(PurchaseOrder.branch)
    )
    
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
            # 1. Update Inventory (Per Branch)
            # Check if inventory exists for this product and branch
            inv_query = select(Inventory).where(
                Inventory.product_id == item.product_id,
                Inventory.branch_id == purchase.branch_id
            )
            inv_result = await db.execute(inv_query)
            inventory = inv_result.scalars().first()
            
            original_stock = 0.0
            
            if inventory:
                original_stock = inventory.quantity
                inventory.quantity += item.quantity
                db.add(inventory)
            else:
                # Create new inventory record
                inventory = Inventory(
                    product_id=item.product_id,
                    branch_id=purchase.branch_id,
                    quantity=item.quantity,
                    location="Main" # Default
                )
                db.add(inventory)
                
            # 2. Create Movement
            movement = InventoryMovement(
                product_id=item.product_id,
                branch_id=purchase.branch_id,
                user_id=current_user.id,
                type=MovementType.IN,
                quantity=item.quantity,
                previous_stock=original_stock,
                new_stock=original_stock + item.quantity,
                reference_id=str(purchase.id),
                reason="Purchase Received"
            )
            db.add(movement)
    
    await db.commit()
    await log_activity(db, "UPDATE_STATUS", "PurchaseOrder", purchase.id, current_user.id, current_user.company_id, {"status": status})
    return purchase

@router.put("/{purchase_id}", response_model=schemas.PurchaseOrder)
async def update_purchase(
    *,
    db: AsyncSession = Depends(get_db),
    purchase_id: UUID,
    purchase_in: schemas.PurchaseOrderUpdate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """
    Update a purchase order (only DRAFT status).
    """
    query = select(PurchaseOrder).where(
        PurchaseOrder.id == purchase_id,
        PurchaseOrder.company_id == current_user.company_id
    ).options(
        selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product).options(
            selectinload(Product.images),
            selectinload(Product.variants),
            selectinload(Product.brand),
            selectinload(Product.unit_of_measure),
            selectinload(Product.purchase_uom),
            selectinload(Product.category)
        ),
        selectinload(PurchaseOrder.supplier),
        selectinload(PurchaseOrder.branch)
    )
    result = await db.execute(query)
    purchase = result.scalars().first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    
    if purchase.status != PurchaseStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Solo se pueden editar órdenes en estado Borrador")
    
    update_data = purchase_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(purchase, field, value)
    
    await db.commit()
    await db.refresh(purchase)
    await log_activity(db, "UPDATE", "PurchaseOrder", purchase.id, current_user.id, current_user.company_id)
    return purchase

@router.delete("/{purchase_id}")
async def delete_purchase(
    *,
    db: AsyncSession = Depends(get_db),
    purchase_id: UUID,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """
    Delete a purchase order. Only DRAFT can be deleted.
    """
    query = select(PurchaseOrder).where(
        PurchaseOrder.id == purchase_id,
        PurchaseOrder.company_id == current_user.company_id
    ).options(selectinload(PurchaseOrder.items))
    result = await db.execute(query)
    purchase = result.scalars().first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    
    if purchase.status != PurchaseStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden eliminar órdenes en estado Borrador"
        )
    
    # Delete items first
    for item in purchase.items:
        await db.delete(item)
    
    await db.delete(purchase)
    await db.commit()
    await log_activity(db, "DELETE", "PurchaseOrder", purchase_id, current_user.id, current_user.company_id)
    return {"ok": True, "detail": "Orden de compra eliminada"}


from fastapi.responses import StreamingResponse
from app.services.pdf_service import PDFService

@router.get("/{purchase_id}/pdf/order")
async def download_pdf(
    *,
    db: AsyncSession = Depends(get_db),
    purchase_id: UUID,
    current_user: User = Depends(PermissionChecker("view_inventory")),
) -> Any:
    """
    Download Purchase Order PDF.
    """
    query = select(PurchaseOrder).where(
        PurchaseOrder.id == purchase_id,
        PurchaseOrder.company_id == current_user.company_id
    ).options(
        selectinload(PurchaseOrder.items).options(
            selectinload(PurchaseOrderItem.product),
            selectinload(PurchaseOrderItem.variant)
        ),
        selectinload(PurchaseOrder.supplier),
        selectinload(PurchaseOrder.branch)
    )
    result = await db.execute(query)
    purchase = result.scalars().first()
    
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
        
    from app.models.company import Company
    result = await db.execute(select(Company).where(Company.id == purchase.company_id))
    company = result.scalars().first()

    service = PDFService()
    
    buffer = service.generate_purchase_order(purchase, company)
    filename = f"OrdenCompra_{str(purchase.id)[:8]}.pdf"
        
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
