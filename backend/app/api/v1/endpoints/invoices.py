from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.endpoints.sales import SaleStatus
from app.core import auth
from app.core.audit import log_activity
from app.core.database import get_db
from app.models.account_ledger import AccountLedger, LedgerType, PartnerType
from app.models.invoice import Invoice, InvoiceItem, InvoicePayment, InvoiceStatus, InvoiceType
from app.models.purchase import PurchaseOrder, PurchaseStatus
from app.models.purchase_item import PurchaseOrderItem
from app.models.sale import Sale, SaleItem
from app.models.supplier import Supplier
from app.models.user import User
from app.models.client import Client
from app.schemas import invoice as schemas

router = APIRouter()


def _permissions(user: User) -> dict:
    return (user.role.permissions if user.role else None) or {}


def _require_invoice_access(user: User, invoice_type: Optional[InvoiceType] = None) -> None:
    if not user.company_id:
        raise HTTPException(status_code=403, detail="Selecciona una empresa para operar documentos financieros")
    permissions = _permissions(user)
    if user.is_superuser or permissions.get("all") or permissions.get("manage_company"):
        return
    required = "manage_sales" if invoice_type == InvoiceType.SALE else "manage_inventory"
    if invoice_type is None:
        if permissions.get("manage_sales") or permissions.get("manage_inventory"):
            return
    elif permissions.get(required):
        return
    raise HTTPException(status_code=403, detail="No tienes permisos para operar facturas de este tipo")


def _invoice_options():
    return [
        selectinload(Invoice.items),
        selectinload(Invoice.payments),
        selectinload(Invoice.client),
        selectinload(Invoice.supplier),
        selectinload(Invoice.branch),
    ]


async def _get_invoice_or_404(db: AsyncSession, invoice_id: UUID, company_id: UUID) -> Invoice:
    result = await db.execute(
        select(Invoice).options(*_invoice_options()).where(
            Invoice.id == invoice_id,
            Invoice.company_id == company_id,
        )
    )
    invoice = result.scalars().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return invoice


async def _next_invoice_number(db: AsyncSession, company_id: UUID, invoice_type: InvoiceType) -> str:
    prefix = "FV" if invoice_type == InvoiceType.SALE else "FC"
    year = datetime.now(timezone.utc).year
    count_result = await db.execute(
        select(func.count(Invoice.id)).where(
            Invoice.company_id == company_id,
            Invoice.type == invoice_type,
        )
    )
    return f"{prefix}-{year}-{(count_result.scalar() or 0) + 1:05d}"


@router.get("/", response_model=List[schemas.InvoiceOut])
async def list_invoices(
    db: AsyncSession = Depends(get_db),
    type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    _require_invoice_access(current_user)
    query = select(Invoice).options(*_invoice_options()).where(Invoice.company_id == current_user.company_id)
    if type:
        try:
            query = query.where(Invoice.type == InvoiceType(type.upper()))
        except ValueError:
            raise HTTPException(status_code=400, detail="Tipo de factura inválido")
    if status:
        try:
            query = query.where(Invoice.status == InvoiceStatus(status.upper()))
        except ValueError:
            raise HTTPException(status_code=400, detail="Estado de factura inválido")
    result = await db.execute(query.order_by(Invoice.created_at.desc()))
    return result.scalars().unique().all()


@router.get("/{invoice_id}", response_model=schemas.InvoiceOut)
async def get_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    _require_invoice_access(current_user)
    invoice = await _get_invoice_or_404(db, invoice_id, current_user.company_id)
    _require_invoice_access(current_user, invoice.type)
    return invoice


@router.post("/from-source", response_model=schemas.InvoiceOut, status_code=201)
async def create_invoice_from_source(
    *,
    db: AsyncSession = Depends(get_db),
    invoice_in: schemas.InvoiceFromSourceCreate,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    try:
        invoice_type = InvoiceType(invoice_in.type.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="Tipo de factura inválido")
    _require_invoice_access(current_user, invoice_type)

    if invoice_type == InvoiceType.SALE:
        source_result = await db.execute(
            select(Sale).options(
                selectinload(Sale.items).selectinload(SaleItem.product),
            ).where(Sale.id == invoice_in.sale_id, Sale.company_id == current_user.company_id)
        )
        sale = source_result.scalars().first()
        if not sale:
            raise HTTPException(status_code=404, detail="Venta no encontrada")
        if not sale.client_id:
            raise HTTPException(status_code=400, detail="La venta debe tener cliente para poder facturarla")
        if sale.status not in {
            SaleStatus.CONFIRMED, SaleStatus.PICKING, SaleStatus.PACKING,
            SaleStatus.DISPATCHED, SaleStatus.DELIVERED, SaleStatus.COMPLETED,
        }:
            raise HTTPException(status_code=400, detail="Confirma la venta antes de facturarla")
        existing = await db.execute(
            select(Invoice.id).where(Invoice.sale_id == sale.id, Invoice.company_id == current_user.company_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="La venta ya tiene una factura")

        invoice = Invoice(
            number=await _next_invoice_number(db, current_user.company_id, invoice_type),
            type=invoice_type,
            branch_id=sale.branch_id,
            client_id=sale.client_id,
            sale_id=sale.id,
            issue_date=datetime.now(timezone.utc),
            due_date=invoice_in.due_date,
            subtotal=sale.subtotal,
            tax=sale.tax,
            total=sale.total,
            notes=invoice_in.notes or sale.notes,
            company_id=current_user.company_id,
            created_by_id=current_user.id,
        )
        db.add(invoice)
        await db.flush()
        for item in sale.items:
            db.add(InvoiceItem(
                invoice_id=invoice.id,
                product_id=item.product_id,
                description=item.product.name if item.product else "Producto",
                quantity=item.quantity,
                unit_price=item.price,
                tax_rate=item.product.tax_rate if item.product else 0.0,
                subtotal=item.total,
                company_id=current_user.company_id,
            ))
    else:
        source_result = await db.execute(
            select(PurchaseOrder).options(
                selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product),
            ).where(PurchaseOrder.id == invoice_in.purchase_id, PurchaseOrder.company_id == current_user.company_id)
        )
        purchase = source_result.scalars().first()
        if not purchase:
            raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
        if not purchase.supplier_id:
            raise HTTPException(status_code=400, detail="La compra debe tener proveedor para poder facturarla")
        if purchase.status != PurchaseStatus.RECEIVED:
            raise HTTPException(status_code=400, detail="Recibe completamente la compra antes de registrar la factura del proveedor")
        existing = await db.execute(
            select(Invoice.id).where(Invoice.purchase_id == purchase.id, Invoice.company_id == current_user.company_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="La compra ya tiene una factura")

        invoice = Invoice(
            number=await _next_invoice_number(db, current_user.company_id, invoice_type),
            type=invoice_type,
            branch_id=purchase.branch_id,
            supplier_id=purchase.supplier_id,
            purchase_id=purchase.id,
            issue_date=datetime.now(timezone.utc),
            due_date=invoice_in.due_date,
            subtotal=purchase.total_amount,
            tax=0.0,
            total=purchase.total_amount,
            notes=invoice_in.notes or purchase.notes,
            company_id=current_user.company_id,
            created_by_id=current_user.id,
        )
        db.add(invoice)
        await db.flush()
        for item in purchase.items:
            db.add(InvoiceItem(
                invoice_id=invoice.id,
                product_id=item.product_id,
                description=item.product.name if item.product else "Producto",
                quantity=item.quantity,
                unit_price=item.unit_cost,
                tax_rate=0.0,
                subtotal=item.subtotal,
                company_id=current_user.company_id,
            ))

    await log_activity(db, "CREATE", "Invoice", invoice.id, current_user.id, current_user.company_id, {"type": invoice.type.value})
    await db.commit()
    return await _get_invoice_or_404(db, invoice.id, current_user.company_id)


@router.post("/{invoice_id}/post", response_model=schemas.InvoiceOut)
async def post_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    invoice = await _get_invoice_or_404(db, invoice_id, current_user.company_id)
    _require_invoice_access(current_user, invoice.type)
    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Solo se pueden contabilizar facturas en borrador")

    if invoice.type == InvoiceType.SALE:
        client_result = await db.execute(select(Client).where(Client.id == invoice.client_id, Client.company_id == current_user.company_id))
        partner = client_result.scalars().first()
        partner_type = PartnerType.CLIENT
        if not partner:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        new_balance = partner.current_balance + invoice.total
        if partner.credit_limit > 0 and new_balance > partner.credit_limit:
            raise HTTPException(status_code=400, detail="La factura excede el límite de crédito del cliente")
    else:
        supplier_result = await db.execute(select(Supplier).where(Supplier.id == invoice.supplier_id, Supplier.company_id == current_user.company_id))
        partner = supplier_result.scalars().first()
        partner_type = PartnerType.SUPPLIER
        if not partner:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        new_balance = partner.current_balance + invoice.total

    partner.current_balance = new_balance
    db.add(AccountLedger(
        partner_id=partner.id,
        partner_type=partner_type,
        type=LedgerType.CHARGE,
        amount=invoice.total,
        balance_after=new_balance,
        reference_id=str(invoice.id),
        description=f"Factura {invoice.number}",
        company_id=current_user.company_id,
        created_by_id=current_user.id,
    ))
    invoice.status = InvoiceStatus.POSTED
    invoice.posted_at = datetime.now(timezone.utc)
    invoice.updated_by_id = current_user.id
    await log_activity(db, "POST", "Invoice", invoice.id, current_user.id, current_user.company_id)
    await db.commit()
    return await _get_invoice_or_404(db, invoice.id, current_user.company_id)


@router.post("/{invoice_id}/payments", response_model=schemas.InvoiceOut)
async def register_invoice_payment(
    invoice_id: UUID,
    payment_in: schemas.InvoicePaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    invoice = await _get_invoice_or_404(db, invoice_id, current_user.company_id)
    _require_invoice_access(current_user, invoice.type)
    if invoice.status not in {InvoiceStatus.POSTED, InvoiceStatus.PARTIALLY_PAID}:
        raise HTTPException(status_code=400, detail="La factura debe estar contabilizada para registrar un pago")
    outstanding = invoice.total - invoice.amount_paid
    if payment_in.amount > outstanding + 0.000001:
        raise HTTPException(status_code=400, detail=f"El pago supera el saldo pendiente ({outstanding:g})")

    model = Client if invoice.type == InvoiceType.SALE else Supplier
    partner_id = invoice.client_id if invoice.type == InvoiceType.SALE else invoice.supplier_id
    partner_result = await db.execute(select(model).where(model.id == partner_id, model.company_id == current_user.company_id))
    partner = partner_result.scalars().first()
    if not partner:
        raise HTTPException(status_code=404, detail="Tercero de la factura no encontrado")

    invoice.amount_paid += payment_in.amount
    invoice.status = InvoiceStatus.PAID if invoice.amount_paid >= invoice.total - 0.000001 else InvoiceStatus.PARTIALLY_PAID
    invoice.updated_by_id = current_user.id
    partner.current_balance -= payment_in.amount
    partner_type = PartnerType.CLIENT if invoice.type == InvoiceType.SALE else PartnerType.SUPPLIER
    db.add(InvoicePayment(
        invoice_id=invoice.id,
        method=payment_in.method.upper().strip(),
        amount=payment_in.amount,
        reference=payment_in.reference.strip() if payment_in.reference else None,
        notes=payment_in.notes.strip() if payment_in.notes else None,
        paid_at=payment_in.paid_at or datetime.now(timezone.utc),
        company_id=current_user.company_id,
        created_by_id=current_user.id,
    ))
    db.add(AccountLedger(
        partner_id=partner.id,
        partner_type=partner_type,
        type=LedgerType.PAYMENT,
        amount=payment_in.amount,
        balance_after=partner.current_balance,
        reference_id=str(invoice.id),
        description=f"Pago de factura {invoice.number}",
        company_id=current_user.company_id,
        created_by_id=current_user.id,
    ))
    await log_activity(db, "PAYMENT", "Invoice", invoice.id, current_user.id, current_user.company_id, {"amount": payment_in.amount})
    await db.commit()
    return await _get_invoice_or_404(db, invoice.id, current_user.company_id)


@router.post("/{invoice_id}/cancel", response_model=schemas.InvoiceOut)
async def cancel_draft_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    invoice = await _get_invoice_or_404(db, invoice_id, current_user.company_id)
    _require_invoice_access(current_user, invoice.type)
    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Una factura contabilizada debe reversarse con nota crédito, no cancelarse")
    invoice.status = InvoiceStatus.CANCELLED
    invoice.cancelled_at = datetime.now(timezone.utc)
    invoice.updated_by_id = current_user.id
    await log_activity(db, "CANCEL", "Invoice", invoice.id, current_user.id, current_user.company_id)
    await db.commit()
    return await _get_invoice_or_404(db, invoice.id, current_user.company_id)
