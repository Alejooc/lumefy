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
from app.models.branch import Branch
from app.models.supplier import Supplier
from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.inventory import Inventory
from app.models.inventory_lot import InventoryLot
from app.models.user import User
from app.core.permissions import PermissionChecker
from app.core.audit import log_activity
from app.schemas import purchase as schemas

router = APIRouter()


def _validate_purchase_status_transition(previous: PurchaseStatus, target: PurchaseStatus) -> None:
    """Validate administrative PO transitions; stock is handled only by /receive."""
    allowed_transitions = {
        PurchaseStatus.DRAFT: {PurchaseStatus.VALIDATION, PurchaseStatus.CANCELLED},
        PurchaseStatus.VALIDATION: {PurchaseStatus.CONFIRMED, PurchaseStatus.CANCELLED},
        PurchaseStatus.CONFIRMED: {PurchaseStatus.CANCELLED},
        PurchaseStatus.PARTIAL: set(),
        PurchaseStatus.RECEIVED: set(),
        PurchaseStatus.CANCELLED: set(),
    }

    if target == PurchaseStatus.RECEIVED:
        raise HTTPException(
            status_code=400,
            detail="La recepción debe registrarse desde 'Recibir productos' para actualizar cantidades e inventario.",
        )
    if target not in allowed_transitions.get(previous, set()):
        raise HTTPException(
            status_code=400,
            detail=f"No se puede cambiar una orden de {previous.value} a {target.value}",
        )


async def _validate_purchase_relations(
    db: AsyncSession,
    purchase_in: schemas.PurchaseOrderCreate,
    company_id: UUID,
) -> None:
    if not purchase_in.items:
        raise HTTPException(status_code=400, detail="La compra debe incluir al menos un producto")

    if not purchase_in.branch_id:
        raise HTTPException(status_code=400, detail="La compra requiere una sucursal de destino")

    branch_result = await db.execute(
        select(Branch.id).where(Branch.id == purchase_in.branch_id, Branch.company_id == company_id)
    )
    if not branch_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")

    if purchase_in.supplier_id:
        supplier_result = await db.execute(
            select(Supplier.id).where(Supplier.id == purchase_in.supplier_id, Supplier.company_id == company_id)
        )
        if not supplier_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    product_ids = {item.product_id for item in purchase_in.items}
    product_result = await db.execute(
        select(Product.id).where(Product.id.in_(product_ids), Product.company_id == company_id)
    )
    if len(product_result.scalars().all()) != len(product_ids):
        raise HTTPException(status_code=404, detail="Uno o más productos no pertenecen a la empresa")

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
        await _validate_purchase_relations(db, purchase_in, current_user.company_id)

        # Create Header
        purchase = PurchaseOrder(
            supplier_id=purchase_in.supplier_id,
            branch_id=purchase_in.branch_id,
            notes=purchase_in.notes,
            expected_date=purchase_in.expected_date,
            order_date=purchase_in.order_date,
            reference_number=purchase_in.reference_number,
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
        purchase.payment_method = purchase_in.payment_method if purchase_in.payment_method else "CASH"

        # Las cuentas por pagar nacen al contabilizar la factura del proveedor,
        # no al crear una orden de compra que todavía puede cambiar o cancelarse.

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
    except HTTPException:
        await db.rollback()
        raise
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
    """Update the administrative state of a purchase order.

    Inventory is deliberately not touched here. It is updated exclusively by the
    receipt endpoint, which records the received quantity per line.
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
        
    _validate_purchase_status_transition(purchase.status, status)
    purchase.status = status
    
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


@router.post("/{purchase_id}/receive", response_model=schemas.PurchaseOrder)
async def receive_purchase(
    purchase_id: UUID,
    *,
    db: AsyncSession = Depends(get_db),
    receive_in: schemas.ReceiveInput,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """
    Receive items for a purchase order (supports partial receipts).
    Each call records the received quantities and creates IN movements.
    """
    # Load PO
    query = select(PurchaseOrder).where(
        PurchaseOrder.id == purchase_id,
        PurchaseOrder.company_id == current_user.company_id
    ).options(
        selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product)
    )
    result = await db.execute(query)
    purchase = result.scalars().first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    if purchase.status in (PurchaseStatus.RECEIVED, PurchaseStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="Purchase Order already received or cancelled")
    if purchase.status not in (PurchaseStatus.CONFIRMED, PurchaseStatus.PARTIAL):
        raise HTTPException(status_code=400, detail="La orden debe estar Confirmada antes de recibir productos")
    if not purchase.branch_id:
        raise HTTPException(status_code=400, detail="La orden requiere una sucursal de destino para recibir productos")

    processed_items = 0
    for ri in receive_in.items:
        # Find item
        item = next((i for i in purchase.items if i.id == ri.item_id), None)
        if not item:
            continue
        if ri.qty_received <= 0:
            continue

        remaining = item.quantity - item.received_qty
        if remaining <= 0:
            raise HTTPException(status_code=400, detail="Uno de los productos ya fue recibido en su totalidad")
        if ri.qty_received > remaining:
            raise HTTPException(status_code=400, detail="La cantidad a recibir supera lo pendiente en una línea de la orden")
        qty_to_receive = ri.qty_received

        tracking_type = (item.product.tracking_type if item.product else "NONE").upper()
        if tracking_type == "LOT" and not (ri.lot_number or "").strip():
            raise HTTPException(status_code=400, detail=f"El producto '{item.product.name}' requiere número de lote")
        if tracking_type == "SERIAL":
            serials = [serial.strip() for serial in (ri.serial_numbers or []) if serial and serial.strip()]
            if qty_to_receive != int(qty_to_receive) or len(serials) != int(qty_to_receive) or len(set(serials)) != len(serials):
                raise HTTPException(
                    status_code=400,
                    detail=f"El producto '{item.product.name}' requiere un serial único por cada unidad recibida",
                )

        item.received_qty += qty_to_receive
        processed_items += 1

        # Update inventory
        inv_result = await db.execute(
            select(Inventory).where(
                Inventory.product_id == item.product_id,
                Inventory.branch_id == purchase.branch_id
            )
        )
        inv = inv_result.scalars().first()

        previous_stock = inv.quantity if inv else 0.0
        new_stock = previous_stock + qty_to_receive

        if inv:
            inv.quantity = new_stock
            inv.average_cost = (
                (previous_stock * inv.average_cost) + (qty_to_receive * item.unit_cost)
            ) / new_stock
        else:
            inv = Inventory(
                product_id=item.product_id,
                branch_id=purchase.branch_id,
                quantity=new_stock,
                average_cost=item.unit_cost,
                company_id=current_user.company_id,
            )
            db.add(inv)

        # Create IN movement
        movement = InventoryMovement(
            product_id=item.product_id,
            branch_id=purchase.branch_id,
            user_id=current_user.id,
            type=MovementType.IN,
            quantity=qty_to_receive,
            previous_stock=previous_stock,
            new_stock=new_stock,
            reason=f"PO Receipt (Order #{str(purchase.id)[:8]})",
            reference_id=str(purchase.id),
            unit_cost=item.unit_cost,
            company_id=current_user.company_id,
        )
        db.add(movement)

        if tracking_type == "LOT":
            lot_number = ri.lot_number.strip()
            lot_result = await db.execute(
                select(InventoryLot).where(
                    InventoryLot.product_id == item.product_id,
                    InventoryLot.branch_id == purchase.branch_id,
                    InventoryLot.lot_number == lot_number,
                    InventoryLot.serial_number.is_(None),
                    InventoryLot.company_id == current_user.company_id,
                )
            )
            lot = lot_result.scalars().first()
            if lot:
                lot.quantity += qty_to_receive
                lot.expiry_date = ri.expiry_date or lot.expiry_date
                lot.unit_cost = item.unit_cost
            else:
                db.add(InventoryLot(
                    product_id=item.product_id,
                    branch_id=purchase.branch_id,
                    lot_number=lot_number,
                    quantity=qty_to_receive,
                    expiry_date=ri.expiry_date,
                    unit_cost=item.unit_cost,
                    source_reference=str(purchase.id),
                    company_id=current_user.company_id,
                    created_by_id=current_user.id,
                ))
        elif tracking_type == "SERIAL":
            serials = [serial.strip() for serial in (ri.serial_numbers or []) if serial and serial.strip()]
            existing_result = await db.execute(
                select(InventoryLot.serial_number).where(
                    InventoryLot.product_id == item.product_id,
                    InventoryLot.serial_number.in_(serials),
                    InventoryLot.company_id == current_user.company_id,
                )
            )
            if existing_result.scalars().first():
                raise HTTPException(status_code=409, detail="Uno de los seriales ya existe para este producto")
            for serial in serials:
                db.add(InventoryLot(
                    product_id=item.product_id,
                    branch_id=purchase.branch_id,
                    serial_number=serial,
                    quantity=1,
                    expiry_date=ri.expiry_date,
                    unit_cost=item.unit_cost,
                    source_reference=str(purchase.id),
                    company_id=current_user.company_id,
                    created_by_id=current_user.id,
                ))

    if not processed_items:
        raise HTTPException(status_code=400, detail="Indica al menos una cantidad válida para recibir")

    # Determine status
    all_received = all(i.received_qty >= i.quantity for i in purchase.items)
    any_received = any(i.received_qty > 0 for i in purchase.items)

    if all_received:
        purchase.status = PurchaseStatus.RECEIVED
    elif any_received:
        purchase.status = PurchaseStatus.PARTIAL
    # else keep current status

    await log_activity(
        db,
        "RECEIVE",
        "PurchaseOrder",
        purchase.id,
        current_user.id,
        current_user.company_id,
        {"status": purchase.status.value, "received_lines": processed_items},
    )
    await db.commit()

    # Reload with full relationships
    return await _load_purchase_detail(db, purchase_id, current_user.company_id)


async def _load_purchase_detail(db: AsyncSession, purchase_id: UUID, company_id: UUID):
    """Helper to load a PO with all relationships."""
    query = select(PurchaseOrder).where(
        PurchaseOrder.id == purchase_id,
        PurchaseOrder.company_id == company_id
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
    return result.scalars().first()

