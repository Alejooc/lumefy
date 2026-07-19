from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import log_activity
from app.core.database import get_db
from app.core.permissions import PermissionChecker
from app.models.branch import Branch
from app.models.product import Product
from app.models.purchase import PurchaseOrder, PurchaseStatus
from app.models.purchase_item import PurchaseOrderItem
from app.models.procurement import (
    PurchaseRequest, PurchaseRequestItem, PurchaseRequestStatus,
    SupplierQuote, SupplierQuoteItem, SupplierQuoteStatus,
)
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas import procurement as schemas

router = APIRouter()


def _request_options():
    return [
        selectinload(PurchaseRequest.items).selectinload(PurchaseRequestItem.product),
        selectinload(PurchaseRequest.quotes).selectinload(SupplierQuote.items).selectinload(SupplierQuoteItem.product),
        selectinload(PurchaseRequest.quotes).selectinload(SupplierQuote.supplier),
    ]


async def _get_request_or_404(db: AsyncSession, request_id: UUID, company_id: UUID) -> PurchaseRequest:
    result = await db.execute(
        select(PurchaseRequest).options(*_request_options()).where(
            PurchaseRequest.id == request_id,
            PurchaseRequest.company_id == company_id,
        )
    )
    request = result.scalars().unique().first()
    if not request:
        raise HTTPException(status_code=404, detail="Solicitud de compra no encontrada")
    return request


async def _validate_request_products_and_branch(
    db: AsyncSession,
    payload: schemas.PurchaseRequestCreate,
    company_id: UUID,
) -> None:
    branch_result = await db.execute(select(Branch.id).where(Branch.id == payload.branch_id, Branch.company_id == company_id))
    if not branch_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    product_ids = {item.product_id for item in payload.items}
    if len(product_ids) != len(payload.items):
        raise HTTPException(status_code=400, detail="No repitas productos en una solicitud de compra")
    products_result = await db.execute(select(Product.id).where(Product.id.in_(product_ids), Product.company_id == company_id))
    if len(products_result.scalars().all()) != len(product_ids):
        raise HTTPException(status_code=404, detail="Uno o más productos no pertenecen a la empresa")


@router.get("/requests", response_model=List[schemas.PurchaseRequestOut])
async def list_purchase_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    result = await db.execute(
        select(PurchaseRequest).options(*_request_options()).where(
            PurchaseRequest.company_id == current_user.company_id,
        ).order_by(PurchaseRequest.created_at.desc())
    )
    return result.scalars().unique().all()


@router.post("/requests", response_model=schemas.PurchaseRequestOut, status_code=201)
async def create_purchase_request(
    *,
    db: AsyncSession = Depends(get_db),
    request_in: schemas.PurchaseRequestCreate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    await _validate_request_products_and_branch(db, request_in, current_user.company_id)
    request = PurchaseRequest(
        branch_id=request_in.branch_id,
        requested_by_id=current_user.id,
        priority=request_in.priority.upper(),
        requested_date=request_in.requested_date,
        notes=request_in.notes,
        status=PurchaseRequestStatus.DRAFT,
        company_id=current_user.company_id,
        created_by_id=current_user.id,
    )
    db.add(request)
    await db.flush()
    for item in request_in.items:
        db.add(PurchaseRequestItem(
            request_id=request.id,
            product_id=item.product_id,
            quantity=item.quantity,
            company_id=current_user.company_id,
        ))
    await log_activity(db, "CREATE", "PurchaseRequest", request.id, current_user.id, current_user.company_id)
    await db.commit()
    return await _get_request_or_404(db, request.id, current_user.company_id)


@router.put("/requests/{request_id}/status", response_model=schemas.PurchaseRequestOut)
async def update_purchase_request_status(
    request_id: UUID,
    status_in: schemas.PurchaseRequestStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    request = await _get_request_or_404(db, request_id, current_user.company_id)
    try:
        target = PurchaseRequestStatus(status_in.status.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="Estado de solicitud inválido")
    transitions = {
        PurchaseRequestStatus.DRAFT: {PurchaseRequestStatus.SUBMITTED, PurchaseRequestStatus.CANCELLED},
        PurchaseRequestStatus.SUBMITTED: {PurchaseRequestStatus.APPROVED, PurchaseRequestStatus.CANCELLED},
        PurchaseRequestStatus.APPROVED: {PurchaseRequestStatus.CANCELLED},
    }
    if target not in transitions.get(request.status, set()):
        raise HTTPException(status_code=400, detail=f"Transición no permitida: {request.status.value} a {target.value}")
    request.status = target
    request.updated_by_id = current_user.id
    await log_activity(db, "UPDATE_STATUS", "PurchaseRequest", request.id, current_user.id, current_user.company_id, {"status": target.value})
    await db.commit()
    return await _get_request_or_404(db, request.id, current_user.company_id)


@router.post("/requests/{request_id}/quotes", response_model=schemas.SupplierQuoteOut, status_code=201)
async def create_supplier_quote(
    request_id: UUID,
    quote_in: schemas.SupplierQuoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    request = await _get_request_or_404(db, request_id, current_user.company_id)
    if request.status not in {PurchaseRequestStatus.SUBMITTED, PurchaseRequestStatus.APPROVED}:
        raise HTTPException(status_code=400, detail="Envía la solicitud para cotizarla")
    supplier_result = await db.execute(select(Supplier.id).where(Supplier.id == quote_in.supplier_id, Supplier.company_id == current_user.company_id))
    if not supplier_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    requested = {item.product_id: item.quantity for item in request.items}
    quoted = {item.product_id: item.quantity for item in quote_in.items}
    if len(quoted) != len(quote_in.items) or quoted != requested:
        raise HTTPException(status_code=400, detail="La cotización debe cubrir exactamente los productos y cantidades solicitados")
    existing = await db.execute(
        select(SupplierQuote.id).where(
            SupplierQuote.request_id == request.id,
            SupplierQuote.supplier_id == quote_in.supplier_id,
            SupplierQuote.status != SupplierQuoteStatus.REJECTED,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Este proveedor ya tiene una cotización vigente para la solicitud")
    quote = SupplierQuote(
        request_id=request.id,
        supplier_id=quote_in.supplier_id,
        status=SupplierQuoteStatus.SUBMITTED,
        reference_number=quote_in.reference_number,
        valid_until=quote_in.valid_until,
        notes=quote_in.notes,
        total_amount=0,
        company_id=current_user.company_id,
        created_by_id=current_user.id,
    )
    db.add(quote)
    await db.flush()
    total = 0.0
    for item in quote_in.items:
        subtotal = item.quantity * item.unit_cost
        total += subtotal
        db.add(SupplierQuoteItem(
            quote_id=quote.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_cost=item.unit_cost,
            subtotal=subtotal,
            company_id=current_user.company_id,
        ))
    quote.total_amount = total
    await log_activity(db, "CREATE", "SupplierQuote", quote.id, current_user.id, current_user.company_id, {"request_id": str(request.id)})
    await db.commit()
    result = await db.execute(
        select(SupplierQuote).options(
            selectinload(SupplierQuote.items),
        ).where(SupplierQuote.id == quote.id)
    )
    return result.scalars().first()


@router.post("/quotes/{quote_id}/accept", response_model=dict)
async def accept_supplier_quote(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    quote_result = await db.execute(
        select(SupplierQuote).options(
            selectinload(SupplierQuote.items),
            selectinload(SupplierQuote.request).selectinload(PurchaseRequest.items),
        ).where(SupplierQuote.id == quote_id, SupplierQuote.company_id == current_user.company_id)
    )
    quote = quote_result.scalars().first()
    if not quote:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    request = quote.request
    if request.status != PurchaseRequestStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Aprueba la solicitud antes de seleccionar una cotización")
    if request.purchase_order_id:
        raise HTTPException(status_code=409, detail="La solicitud ya fue convertida en una orden de compra")
    if quote.status != SupplierQuoteStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail="Solo se puede aceptar una cotización enviada")

    purchase = PurchaseOrder(
        supplier_id=quote.supplier_id,
        branch_id=request.branch_id,
        user_id=current_user.id,
        company_id=current_user.company_id,
        status=PurchaseStatus.DRAFT,
        payment_method="CREDIT",
        total_amount=quote.total_amount,
        notes=f"Generada desde solicitud {str(request.id)[:8]}. {quote.notes or ''}".strip(),
        reference_number=quote.reference_number,
    )
    db.add(purchase)
    await db.flush()
    for item in quote.items:
        db.add(PurchaseOrderItem(
            purchase_id=purchase.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_cost=item.unit_cost,
            subtotal=item.subtotal,
            company_id=current_user.company_id,
        ))
    quote.status = SupplierQuoteStatus.ACCEPTED
    request.status = PurchaseRequestStatus.CONVERTED
    request.purchase_order_id = purchase.id
    request.updated_by_id = current_user.id
    other_quotes = (await db.execute(
        select(SupplierQuote).where(
            SupplierQuote.request_id == request.id,
            SupplierQuote.id != quote.id,
            SupplierQuote.status == SupplierQuoteStatus.SUBMITTED,
        )
    )).scalars().all()
    for other_quote in other_quotes:
        other_quote.status = SupplierQuoteStatus.REJECTED
    await log_activity(db, "ACCEPT", "SupplierQuote", quote.id, current_user.id, current_user.company_id, {"purchase_id": str(purchase.id)})
    await db.commit()
    return {"purchase_id": str(purchase.id), "request_id": str(request.id), "quote_id": str(quote.id)}
