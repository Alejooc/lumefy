from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.sale import Sale, SaleItem, SaleStatus, Payment
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement, MovementType
from app.services.outbox import enqueue_outbox_event
from app.models.product import Product
from app.models.branch import Branch
from app.models.warehouse import Warehouse
from app.models.client import Client
from app.models.logistics import SalePackage, SalePackageItem
from app.models.user import User
from app.core.permissions import PermissionChecker
from app.services.inventory_consumption import consume_fifo_lots
from app.schemas import sale as schemas
import uuid
from datetime import datetime

router = APIRouter()


async def _validate_sale_relations(db: AsyncSession, sale_in: schemas.SaleCreate, company_id: uuid.UUID) -> None:
    if not sale_in.items:
        raise HTTPException(status_code=400, detail="La venta debe incluir al menos un producto")

    branch_result = await db.execute(
        select(Branch.id).where(Branch.id == sale_in.branch_id, Branch.company_id == company_id)
    )
    if not branch_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")

    if sale_in.client_id:
        client_result = await db.execute(
            select(Client.id).where(Client.id == sale_in.client_id, Client.company_id == company_id)
        )
        if not client_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

    product_ids = {item.product_id for item in sale_in.items}
    product_result = await db.execute(
        select(Product.id).where(Product.id.in_(product_ids), Product.company_id == company_id)
    )
    if len(product_result.scalars().all()) != len(product_ids):
        raise HTTPException(status_code=404, detail="Uno o más productos no pertenecen a la empresa")

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

@router.get("/export")
async def export_sales(
    db: AsyncSession = Depends(get_db),
    format: str = "excel",
    status: str = None,
    date_from: str = None,
    date_to: str = None,
    current_user: User = Depends(PermissionChecker("view_sales")),
) -> Any:
    """Export sales to Excel or CSV."""
    from app.services.export_service import ExportService

    query = select(Sale).options(
        selectinload(Sale.client),
        selectinload(Sale.user),
        selectinload(Sale.branch),
    ).where(Sale.company_id == current_user.company_id).order_by(Sale.created_at.desc())

    if status:
        query = query.where(Sale.status == status)
    if date_from:
        query = query.where(Sale.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.where(Sale.created_at <= datetime.fromisoformat(date_to))

    result = await db.execute(query)
    sales = result.scalars().all()

    columns = {
        "order_number": "# Orden",
        "created_at": "Fecha",
        "client_name": "Cliente",
        "branch_name": "Sucursal",
        "status": "Estado",
        "subtotal": "Subtotal",
        "tax_amount": "Impuesto",
        "total": "Total",
        "user_name": "Vendedor",
    }

    rows = []
    for s in sales:
        rows.append({
            "order_number": s.order_number or "",
            "created_at": s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "",
            "client_name": s.client.name if s.client else "Consumidor Final",
            "branch_name": s.branch.name if s.branch else "",
            "status": s.status or "",
            "subtotal": float(s.subtotal) if s.subtotal else 0,
            "tax_amount": float(s.tax_amount) if s.tax_amount else 0,
            "total": float(s.total) if s.total else 0,
            "user_name": s.user.full_name if s.user else "",
        })

    if format == "csv":
        return ExportService.to_csv_response(rows, columns, filename="ventas")
    return ExportService.to_excel_response(rows, columns, filename="ventas")

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
        await _validate_sale_relations(db, sale_in, current_user.company_id)

        initial_status = SaleStatus(sale_in.status or SaleStatus.DRAFT)
        if initial_status not in (SaleStatus.DRAFT, SaleStatus.QUOTE):
            raise HTTPException(status_code=400, detail="Una venta nueva debe iniciar en Borrador o Cotización")

        warehouse = await db.scalar(select(Warehouse).where(
            Warehouse.branch_id == sale_in.branch_id,
            Warehouse.is_active.is_(True),
        ).order_by(Warehouse.is_default.desc(), Warehouse.name))
        if not warehouse:
            raise HTTPException(status_code=400, detail="La sucursal no tiene una bodega activa para la venta")

        # 1. Create Sale Header
        sale = Sale(
            branch_id=sale_in.branch_id,
            warehouse_id=warehouse.id,
            user_id=current_user.id,
            client_id=sale_in.client_id,
            status=initial_status,
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
        
        # Las cuentas por cobrar se generan al contabilizar una factura. Una
        # orden comercial por sí sola no debe modificar el saldo del cliente.

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
                    link=f"/sales/view/{sale.id}"
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

    except HTTPException:
        await db.rollback()
        raise
    except (TypeError, ValueError) as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
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
    try:
        new_status = SaleStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Estado de venta inválido")
    
    if old_status == new_status:
        return sale
        
    
    # LOGIC:
    # 1. DRAFT/QUOTE -> CONFIRMED (Reserve Inventory)
    # 2. CONFIRMED -> PICKING
    # 3. PICKING -> PACKING
    # 4. PACKING -> DISPATCHED
    # 5. DISPATCHED -> DELIVERED
    # 6. Pre-dispatch -> CANCELLED (Release reservations)
    
    # Allow flow
    valid_transitions = {
        SaleStatus.DRAFT: [SaleStatus.CONFIRMED, SaleStatus.CANCELLED],
        SaleStatus.QUOTE: [SaleStatus.CONFIRMED, SaleStatus.CANCELLED],
        SaleStatus.CONFIRMED: [SaleStatus.PICKING, SaleStatus.CANCELLED],
        SaleStatus.PICKING: [SaleStatus.PACKING, SaleStatus.CANCELLED],
        SaleStatus.PACKING: [SaleStatus.DISPATCHED, SaleStatus.CANCELLED],
        SaleStatus.DISPATCHED: [SaleStatus.DELIVERED],
        SaleStatus.DELIVERED: [SaleStatus.COMPLETED],
        SaleStatus.COMPLETED: [],
        SaleStatus.CANCELLED: [], # Final state (unless we allow re-drafting later)
    }
    
    if new_status not in valid_transitions.get(old_status, []):
        raise HTTPException(status_code=400, detail=f"Transición no permitida: {old_status.value} a {new_status.value}")

    physical_items = [
        item for item in sale.items
        if not item.product or item.product.product_type != "SERVICE"
    ]
    if new_status == SaleStatus.PACKING:
        incomplete = [item for item in physical_items if item.quantity_picked < item.quantity]
        if incomplete:
            raise HTTPException(
                status_code=400,
                detail="Finaliza el picking de todas las unidades antes de pasar a empaque",
            )

    if new_status == SaleStatus.DISPATCHED:
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
        incomplete = [
            item for item in physical_items
            if float(packed_by_item.get(item.id, 0)) < item.quantity
        ]
        if incomplete:
            raise HTTPException(
                status_code=400,
                detail="Empaca todas las unidades antes de despachar la orden",
            )

    if new_status == SaleStatus.CONFIRMED and old_status in [SaleStatus.DRAFT, SaleStatus.QUOTE]:
        # Confirmation reserves stock; the physical exit is recorded only on dispatch.
        # This keeps availability accurate without lowering on-hand stock prematurely.
        required_by_product = {}
        for item in sale.items:
            if not item.product or not item.product.track_inventory:
                continue
            required_by_product[item.product_id] = required_by_product.get(item.product_id, 0.0) + item.quantity

        for product_id, requested_quantity in required_by_product.items():
            product = next(item.product for item in sale.items if item.product_id == product_id)
            inv_result = await db.execute(select(Inventory).where(
                Inventory.product_id == product_id,
                Inventory.branch_id == sale.branch_id,
                Inventory.warehouse_id == sale.warehouse_id,
            ).with_for_update())
            inventory = inv_result.scalars().first()
            available = (inventory.quantity - inventory.reserved_quantity) if inventory else 0
            if available < requested_quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stock insuficiente para confirmar '{product.name}'. Disponible: {available:g}",
                )

        for item in sale.items:
            if item.product and item.product.track_inventory:
                inv_result = await db.execute(select(Inventory).where(
                    Inventory.product_id == item.product_id,
                    Inventory.branch_id == sale.branch_id,
                    Inventory.warehouse_id == sale.warehouse_id,
                ))
                inventory = inv_result.scalars().first()
                # The first pass guarantees that an inventory row and free stock exist.
                inventory.reserved_quantity += item.quantity
                db.add(InventoryMovement(
                    product_id=item.product_id,
                    branch_id=sale.branch_id,
                    warehouse_id=sale.warehouse_id,
                    user_id=current_user.id,
                    type=MovementType.RESERVE,
                    quantity=0.0,
                    previous_stock=inventory.quantity,
                    new_stock=inventory.quantity,
                    unit_cost=inventory.average_cost,
                    reference_id=str(sale.id),
                    reason=f"Reserva de orden de venta ({item.quantity:g} unidades)",
                    company_id=current_user.company_id,
                ))

    elif new_status == SaleStatus.DISPATCHED and old_status == SaleStatus.PACKING:
        # Dispatch is the inventory event: consume the reservation and record kardex.
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
                
    elif new_status == SaleStatus.CANCELLED and old_status in [SaleStatus.CONFIRMED, SaleStatus.PICKING, SaleStatus.PACKING]:
        for item in sale.items:
            if item.product and item.product.track_inventory:
                inv_result = await db.execute(select(Inventory).where(
                    Inventory.product_id == item.product_id,
                    Inventory.branch_id == sale.branch_id,
                    Inventory.warehouse_id == sale.warehouse_id,
                ))
                inventory = inv_result.scalars().first()
                
                if not inventory:
                    inventory = Inventory(
                        product_id=item.product_id,
                        branch_id=sale.branch_id,
                        warehouse_id=sale.warehouse_id,
                        quantity=0.0,
                        company_id=current_user.company_id,
                    )
                    db.add(inventory)
                if inventory.reserved_quantity < item.quantity:
                    raise HTTPException(status_code=400, detail=f"La reserva de '{item.product.name}' no puede liberarse")
                else:
                    inventory.reserved_quantity -= item.quantity
                    db.add(InventoryMovement(
                        product_id=item.product_id,
                        branch_id=sale.branch_id,
                        warehouse_id=sale.warehouse_id,
                        user_id=current_user.id,
                        type=MovementType.RELEASE,
                        quantity=0.0,
                        previous_stock=inventory.quantity,
                        new_stock=inventory.quantity,
                        unit_cost=inventory.average_cost,
                        reference_id=str(sale.id),
                        reason=f"Reserva liberada por cancelación ({item.quantity:g} unidades)",
                        company_id=current_user.company_id,
                    ))
    
    sale.status = new_status
    if new_status == SaleStatus.CONFIRMED:
        enqueue_outbox_event(
            db, event_type="inventory.reserved", aggregate_type="sale", aggregate_id=sale.id,
            company_id=current_user.company_id,
            payload={"sale_id": str(sale.id), "warehouse_id": str(sale.warehouse_id) if sale.warehouse_id else None, "source": "sales"},
        )
    elif new_status == SaleStatus.CANCELLED:
        enqueue_outbox_event(
            db, event_type="inventory.released", aggregate_type="sale", aggregate_id=sale.id,
            company_id=current_user.company_id,
            payload={"sale_id": str(sale.id), "warehouse_id": str(sale.warehouse_id) if sale.warehouse_id else None, "source": "sales"},
        )
    elif new_status == SaleStatus.DISPATCHED:
        enqueue_outbox_event(
            db, event_type="inventory.dispatched", aggregate_type="sale", aggregate_id=sale.id,
            company_id=current_user.company_id,
            payload={"sale_id": str(sale.id), "warehouse_id": str(sale.warehouse_id) if sale.warehouse_id else None, "source": "sales"},
        )
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


# ──────────── Delivery & Completion ────────────

@router.post("/{sale_id}/deliver", response_model=schemas.Sale)
async def confirm_delivery(
    *,
    db: AsyncSession = Depends(get_db),
    sale_id: uuid.UUID,
    delivery_in: schemas.DeliveryConfirmation,
    current_user: User = Depends(PermissionChecker("manage_sales")),
) -> Any:
    """Confirm delivery of a dispatched sale."""
    result = await db.execute(
        select(Sale).options(
            selectinload(Sale.items).selectinload(SaleItem.product).options(
                selectinload(Product.images),
                selectinload(Product.variants),
                selectinload(Product.brand),
                selectinload(Product.unit_of_measure),
                selectinload(Product.purchase_uom),
                selectinload(Product.category),
            ),
            selectinload(Sale.payments),
            selectinload(Sale.user),
            selectinload(Sale.branch),
            selectinload(Sale.client),
        ).where(
            Sale.id == sale_id,
            Sale.company_id == current_user.company_id,
        )
    )
    sale = result.scalars().first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    if sale.status != SaleStatus.DISPATCHED:
        raise HTTPException(status_code=400, detail=f"Sale must be DISPATCHED to confirm delivery. Current: {sale.status.value}")

    from datetime import datetime, timezone
    sale.status = SaleStatus.DELIVERED
    sale.delivered_at = datetime.now(timezone.utc)
    sale.delivery_notes = delivery_in.notes
    sale.delivery_evidence_url = delivery_in.evidence_url

    await db.commit()
    await db.refresh(sale)
    return sale


@router.post("/{sale_id}/complete", response_model=schemas.Sale)
async def complete_sale(
    *,
    db: AsyncSession = Depends(get_db),
    sale_id: uuid.UUID,
    current_user: User = Depends(PermissionChecker("manage_sales")),
) -> Any:
    """Mark a delivered sale as completed."""
    result = await db.execute(
        select(Sale).options(
            selectinload(Sale.items).selectinload(SaleItem.product).options(
                selectinload(Product.images),
                selectinload(Product.variants),
                selectinload(Product.brand),
                selectinload(Product.unit_of_measure),
                selectinload(Product.purchase_uom),
                selectinload(Product.category),
            ),
            selectinload(Sale.payments),
            selectinload(Sale.user),
            selectinload(Sale.branch),
            selectinload(Sale.client),
        ).where(
            Sale.id == sale_id,
            Sale.company_id == current_user.company_id,
        )
    )
    sale = result.scalars().first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    if sale.status != SaleStatus.DELIVERED:
        raise HTTPException(status_code=400, detail=f"Sale must be DELIVERED to complete. Current: {sale.status.value}")

    from datetime import datetime, timezone
    sale.status = SaleStatus.COMPLETED
    sale.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(sale)
    return sale

