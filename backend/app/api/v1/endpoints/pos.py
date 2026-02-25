from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.sale import Sale, SaleItem, SaleStatus, Payment
from app.models.branch import Branch
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.pos_session import POSSession, POSSessionStatus
from app.models.user import User
from app.models.category import Category
from app.models.company_app_install import CompanyAppInstall
from app.models.app_definition import AppDefinition
from app.core.permissions import PermissionChecker
from app.schemas import pos as schemas
import uuid
from datetime import datetime, timezone

router = APIRouter()

DEFAULT_POS_SETTINGS = {
    "show_sessions_manager": True,
    "session_visibility_scope": "branch",
    "allow_multiple_open_sessions_per_branch": True,
    "allow_enter_other_user_session": False,
    "require_manager_for_void": True,
}


async def _load_pos_install(
    db: AsyncSession,
    current_user: User,
) -> tuple[CompanyAppInstall, AppDefinition]:
    result = await db.execute(
        select(CompanyAppInstall, AppDefinition).join(AppDefinition).where(
            CompanyAppInstall.company_id == current_user.company_id,
            AppDefinition.slug == "pos_module",
            CompanyAppInstall.is_enabled == True
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=403, detail="POS Module is not installed for this company.")
    return row


async def _load_pos_settings(
    db: AsyncSession,
    current_user: User,
) -> dict:
    install, app = await _load_pos_install(db, current_user)
    settings: dict = {}
    settings.update(DEFAULT_POS_SETTINGS)
    settings.update(app.default_config or {})
    settings.update(install.settings or {})
    return settings


async def _compute_cash_sales_total(db: AsyncSession, session_id: uuid.UUID) -> float:
    total_result = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0.0))
        .join(Sale, Payment.sale_id == Sale.id)
        .where(
            Sale.pos_session_id == session_id,
            Payment.method == "CASH"
        )
    )
    return float(total_result.scalar() or 0.0)


async def _compute_session_sales_breakdown(db: AsyncSession, session_id: uuid.UUID) -> tuple[float, float, float, int]:
    result = await db.execute(
        select(
            func.coalesce(func.sum(Payment.amount), 0.0).label("total_sales"),
            func.coalesce(func.sum(Payment.amount).filter(Payment.method == "CASH"), 0.0).label("cash_total"),
            func.coalesce(func.sum(Payment.amount).filter(Payment.method == "CARD"), 0.0).label("card_total"),
            func.coalesce(func.sum(Payment.amount).filter(Payment.method == "CREDIT"), 0.0).label("credit_total"),
            func.count(func.distinct(Payment.sale_id)).label("tx_count"),
        )
        .join(Sale, Payment.sale_id == Sale.id)
        .where(Sale.pos_session_id == session_id)
    )
    row = result.one()
    return (
        float(row.total_sales or 0.0),
        float(row.cash_total or 0.0),
        float(row.card_total or 0.0),
        float(row.credit_total or 0.0),
        int(row.tx_count or 0),
    )


def _session_out(session: POSSession, cash_sales_total: float, expected_amount: float | None = None) -> schemas.POSSessionOut:
    expected = expected_amount if expected_amount is not None else session.expected_amount
    return schemas.POSSessionOut(
        id=session.id,
        branch_id=session.branch_id,
        user_id=session.user_id,
        status=schemas.POSSessionStatus(session.status.value if hasattr(session.status, "value") else str(session.status)),
        opened_at=session.opened_at,
        closed_at=session.closed_at,
        opening_amount=session.opening_amount,
        counted_amount=session.counted_amount,
        expected_amount=expected,
        over_short=session.over_short,
        closing_note=session.closing_note,
        cash_sales_total=cash_sales_total
    )

# Dependency to check if POS app is active for company
async def check_pos_app(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("create_sales")) # Use existing permission
):
    install, _app = await _load_pos_install(db, current_user)
    granted_scopes = install.granted_scopes or []
    if granted_scopes and "sales:create" not in granted_scopes:
        raise HTTPException(status_code=403, detail="POS app requires scope 'sales:create'.")
    return current_user


@router.get("/config", response_model=schemas.POSConfigOut)
async def get_pos_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_pos_app)
) -> Any:
    settings = await _load_pos_settings(db, current_user)
    scope_value = str(settings.get("session_visibility_scope") or "branch").lower()
    if scope_value not in {"own", "branch", "company"}:
        scope_value = "branch"
    return schemas.POSConfigOut(
        show_sessions_manager=bool(settings.get("show_sessions_manager", True)),
        session_visibility_scope=schemas.POSSessionVisibilityScope(scope_value),
        allow_multiple_open_sessions_per_branch=bool(settings.get("allow_multiple_open_sessions_per_branch", True)),
        allow_enter_other_user_session=bool(settings.get("allow_enter_other_user_session", False)),
        require_manager_for_void=bool(settings.get("require_manager_for_void", True)),
    )


@router.get("/products", response_model=List[schemas.POSProduct])
async def get_pos_products(
    branch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_pos_app)
) -> Any:
    """
    Optimized endpoint to fetch all products and their stock for the POS interface.
    """
    query = select(Product, Inventory, Category).outerjoin(
        Inventory, 
        and_(Inventory.product_id == Product.id, Inventory.branch_id == branch_id)
    ).outerjoin(
        Category, Category.id == Product.category_id
    ).where(Product.company_id == current_user.company_id, Product.is_active == True)
    
    result = await db.execute(query)
    rows = result.all()
    
    products = []
    for product, inventory, category in rows:
        products.append({
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "barcode": product.barcode,
            "price": product.price,
            "stock": inventory.quantity if inventory else 0.0,
            "category_id": product.category_id,
            "category_name": category.name if category else None,
            "image_url": product.image_url
        })
        
    return products


@router.get("/sessions/current", response_model=schemas.POSSessionOut | None)
async def get_current_pos_session(
    branch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_pos_app)
) -> Any:
    result = await db.execute(
        select(POSSession).where(
            POSSession.company_id == current_user.company_id,
            POSSession.user_id == current_user.id,
            POSSession.branch_id == branch_id,
            POSSession.status == POSSessionStatus.OPEN
        )
    )
    session = result.scalars().first()
    if not session:
        return None

    cash_sales_total = await _compute_cash_sales_total(db, session.id)
    expected_amount = session.opening_amount + cash_sales_total

    return _session_out(session, cash_sales_total, expected_amount=expected_amount)


@router.get("/sessions", response_model=List[schemas.POSSessionListItem])
async def list_pos_sessions(
    branch_id: uuid.UUID | None = None,
    status: schemas.POSSessionStatus | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_pos_app)
) -> Any:
    settings = await _load_pos_settings(db, current_user)
    if not bool(settings.get("show_sessions_manager", True)):
        raise HTTPException(status_code=403, detail="El gestor de cajas esta deshabilitado en la configuracion del POS.")

    scope = str(settings.get("session_visibility_scope") or "branch").lower()
    if scope not in {"own", "branch", "company"}:
        scope = "branch"

    safe_limit = max(1, min(limit, 200))
    query = (
        select(POSSession, Branch.name, User.full_name, User.email)
        .join(Branch, Branch.id == POSSession.branch_id)
        .join(User, User.id == POSSession.user_id)
        .where(POSSession.company_id == current_user.company_id)
    )
    current_branch_id = getattr(current_user, "branch_id", None)
    if scope == "own":
        query = query.where(POSSession.user_id == current_user.id)
    elif scope == "branch":
        if current_branch_id:
            query = query.where(POSSession.branch_id == current_branch_id)
        elif branch_id:
            query = query.where(POSSession.branch_id == branch_id)
        else:
            query = query.where(POSSession.user_id == current_user.id)

    if branch_id:
        query = query.where(POSSession.branch_id == branch_id)
    if status:
        query = query.where(POSSession.status == POSSessionStatus(status.value))

    query = query.order_by(POSSession.opened_at.desc()).limit(safe_limit)
    rows = (await db.execute(query)).all()
    response: list[schemas.POSSessionListItem] = []
    for session, branch_name, user_full_name, user_email in rows:
        total_sales, cash_total, _card_total, _credit_total, tx_count = await _compute_session_sales_breakdown(db, session.id)
        expected_amount = session.opening_amount + cash_total if session.status == POSSessionStatus.OPEN else session.expected_amount
        response.append(
            schemas.POSSessionListItem(
                id=session.id,
                branch_id=session.branch_id,
                branch_name=branch_name,
                user_id=session.user_id,
                user_name=user_full_name or user_email,
                status=schemas.POSSessionStatus(session.status.value),
                opened_at=session.opened_at,
                closed_at=session.closed_at,
                opening_amount=session.opening_amount,
                expected_amount=expected_amount,
                counted_amount=session.counted_amount,
                over_short=session.over_short,
                cash_sales_total=cash_total,
                total_sales=total_sales,
                transactions_count=tx_count
            )
        )
    return response


@router.get("/sessions/{session_id}/stats", response_model=schemas.POSSessionStatsOut)
async def get_pos_session_stats(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_pos_app)
) -> Any:
    settings = await _load_pos_settings(db, current_user)
    if not bool(settings.get("show_sessions_manager", True)):
        raise HTTPException(status_code=403, detail="El gestor de cajas esta deshabilitado en la configuracion del POS.")

    result = await db.execute(
        select(POSSession, Branch.name, User.full_name, User.email)
        .join(Branch, Branch.id == POSSession.branch_id)
        .join(User, User.id == POSSession.user_id)
        .where(
            POSSession.id == session_id,
            POSSession.company_id == current_user.company_id
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Sesion POS no encontrada.")

    session, branch_name, user_full_name, user_email = row
    current_branch_id = getattr(current_user, "branch_id", None)
    scope = str(settings.get("session_visibility_scope") or "branch").lower()
    if scope == "own" and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes ver estadisticas de caja de otro usuario.")
    if scope == "branch" and current_branch_id and session.branch_id != current_branch_id:
        raise HTTPException(status_code=403, detail="No puedes ver estadisticas de cajas de otra sucursal.")

    total_sales, cash_total, card_total, credit_total, tx_count = await _compute_session_sales_breakdown(db, session.id)
    expected_amount = session.opening_amount + cash_total if session.status == POSSessionStatus.OPEN else session.expected_amount
    average_ticket = (total_sales / tx_count) if tx_count > 0 else 0.0

    return schemas.POSSessionStatsOut(
        id=session.id,
        branch_id=session.branch_id,
        branch_name=branch_name,
        user_id=session.user_id,
        user_name=user_full_name or user_email,
        status=schemas.POSSessionStatus(session.status.value),
        opened_at=session.opened_at,
        closed_at=session.closed_at,
        opening_amount=session.opening_amount,
        expected_amount=expected_amount,
        counted_amount=session.counted_amount,
        over_short=session.over_short,
        transactions_count=tx_count,
        total_sales=total_sales,
        cash_sales_total=cash_total,
        card_sales_total=card_total,
        credit_sales_total=credit_total,
        average_ticket=average_ticket
    )


@router.post("/sessions/open", response_model=schemas.POSSessionOut)
async def open_pos_session(
    payload: schemas.POSSessionOpenIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_pos_app)
) -> Any:
    settings = await _load_pos_settings(db, current_user)

    existing_result = await db.execute(
        select(POSSession).where(
            POSSession.company_id == current_user.company_id,
            POSSession.user_id == current_user.id,
            POSSession.branch_id == payload.branch_id,
            POSSession.status == POSSessionStatus.OPEN
        )
    )
    existing_session = existing_result.scalars().first()
    if existing_session:
        cash_sales_total = await _compute_cash_sales_total(db, existing_session.id)
        expected_amount = existing_session.opening_amount + cash_sales_total
        return _session_out(existing_session, cash_sales_total, expected_amount=expected_amount)

    allow_multi = bool(settings.get("allow_multiple_open_sessions_per_branch", True))
    if not allow_multi:
        branch_open_result = await db.execute(
            select(POSSession).where(
                POSSession.company_id == current_user.company_id,
                POSSession.branch_id == payload.branch_id,
                POSSession.status == POSSessionStatus.OPEN
            )
        )
        branch_open_session = branch_open_result.scalars().first()
        if branch_open_session:
            raise HTTPException(
                status_code=400,
                detail="Ya existe una caja abierta en esta sucursal. Cierra la caja actual o habilita multiples cajas en configuracion POS."
            )

    session = POSSession(
        company_id=current_user.company_id,
        branch_id=payload.branch_id,
        user_id=current_user.id,
        status=POSSessionStatus.OPEN,
        opened_at=datetime.now(timezone.utc),
        opening_amount=max(payload.opening_amount, 0.0),
        counted_amount=0.0,
        expected_amount=max(payload.opening_amount, 0.0),
        over_short=0.0,
        closing_note=payload.opening_note
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return _session_out(session, cash_sales_total=0.0, expected_amount=session.opening_amount)


@router.post("/sessions/{session_id}/close", response_model=schemas.POSSessionOut)
async def close_pos_session(
    session_id: uuid.UUID,
    payload: schemas.POSSessionCloseIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_pos_app)
) -> Any:
    result = await db.execute(
        select(POSSession).where(
            POSSession.id == session_id,
            POSSession.company_id == current_user.company_id,
            POSSession.user_id == current_user.id
        )
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesion POS no encontrada.")

    if session.status != POSSessionStatus.OPEN:
        raise HTTPException(status_code=400, detail="La caja ya esta cerrada.")

    cash_sales_total = await _compute_cash_sales_total(db, session.id)
    expected_amount = session.opening_amount + cash_sales_total
    counted_amount = payload.counted_amount

    session.status = POSSessionStatus.CLOSED
    session.closed_at = datetime.now(timezone.utc)
    session.expected_amount = expected_amount
    session.counted_amount = counted_amount
    session.over_short = counted_amount - expected_amount
    session.closing_note = payload.closing_note

    await db.commit()
    await db.refresh(session)

    return _session_out(session, cash_sales_total=cash_sales_total, expected_amount=expected_amount)


@router.post("/sales/{sale_id}/void", response_model=schemas.POSVoidOut)
async def void_pos_sale(
    sale_id: uuid.UUID,
    payload: schemas.POSVoidIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_pos_app)
) -> Any:
    result = await db.execute(
        select(Sale).options(
            selectinload(Sale.items).selectinload(SaleItem.product),
            selectinload(Sale.client)
        ).where(
            Sale.id == sale_id,
            Sale.company_id == current_user.company_id
        )
    )
    sale = result.scalars().first()
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada.")

    if sale.status == SaleStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="La venta ya esta anulada.")

    if sale.status != SaleStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Solo se pueden anular ventas POS completadas.")

    if sale.payment_method == "CREDIT":
        raise HTTPException(status_code=400, detail="Las ventas a credito deben devolverse desde modulo de devoluciones.")

    for item in sale.items:
        inv_result = await db.execute(
            select(Inventory).where(
                Inventory.product_id == item.product_id,
                Inventory.branch_id == sale.branch_id
            )
        )
        inventory = inv_result.scalars().first()
        if not inventory:
            inventory = Inventory(
                product_id=item.product_id,
                branch_id=sale.branch_id,
                quantity=0.0,
                company_id=current_user.company_id
            )
            db.add(inventory)

        previous_stock = inventory.quantity
        inventory.quantity = previous_stock + item.quantity

        movement = InventoryMovement(
            product_id=item.product_id,
            branch_id=sale.branch_id,
            user_id=current_user.id,
            type=MovementType.IN,
            quantity=item.quantity,
            previous_stock=previous_stock,
            new_stock=inventory.quantity,
            reference_id=str(sale.id),
            reason=f"Anulacion POS: {payload.reason or 'Sin motivo'}",
            company_id=current_user.company_id
        )
        db.add(movement)

    sale.status = SaleStatus.CANCELLED
    note = payload.reason or "Sin motivo"
    sale.notes = f"{sale.notes or ''}\n[POS VOID] {note}".strip()

    await db.commit()
    await db.refresh(sale)

    return schemas.POSVoidOut(
        success=True,
        sale_id=sale.id,
        status=sale.status.value,
        detail="Venta anulada y stock restaurado."
    )


@router.post("/checkout", response_model=dict)
async def pos_checkout(
    *,
    db: AsyncSession = Depends(get_db),
    checkout_in: schemas.POSCheckout,
    current_user: User = Depends(check_pos_app)
) -> Any:
    """
    Fast checkout logic for POS:
    1. Creates Sale in COMPLETED status.
    2. Deducts Inventory instantly.
    3. Registers Payment.
    """
    try:
        session_result = await db.execute(
            select(POSSession).where(
                POSSession.company_id == current_user.company_id,
                POSSession.user_id == current_user.id,
                POSSession.branch_id == checkout_in.branch_id,
                POSSession.status == POSSessionStatus.OPEN
            )
        )
        open_session = session_result.scalars().first()
        if not open_session:
            raise HTTPException(status_code=400, detail="Debes abrir caja antes de cobrar en POS.")

        # 1. Create Sale Header
        sale = Sale(
            branch_id=checkout_in.branch_id,
            user_id=current_user.id,
            pos_session_id=open_session.id,
            client_id=checkout_in.client_id,
            status=SaleStatus.COMPLETED, # Instantly completed
            payment_method=checkout_in.payment_method,
            notes=checkout_in.notes or "Venta POS",
            subtotal=0.0,
            tax=0.0,
            discount=0.0,
            total=0.0,
            company_id=current_user.company_id,
            completed_at=datetime.now(timezone.utc),
            delivered_at=datetime.now(timezone.utc)
        )
        db.add(sale)
        await db.flush()
        
        total_amount = 0.0
        
        # 2. Process Items and Inventory
        for item_in in checkout_in.items:
            # Sale Item
            item_total = (item_in.price * item_in.quantity) - item_in.discount
            total_amount += item_total
            
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=item_in.product_id,
                quantity=item_in.quantity,
                quantity_picked=item_in.quantity, # Fully picked
                price=item_in.price,
                discount=item_in.discount,
                total=item_total
            )
            db.add(sale_item)
            
            # Inventory Deduction
            inv_result = await db.execute(
                select(Inventory).where(
                    Inventory.product_id == item_in.product_id,
                    Inventory.branch_id == checkout_in.branch_id
                )
            )
            inventory = inv_result.scalars().first()
            if not inventory:
                inventory = Inventory(
                    product_id=item_in.product_id,
                    branch_id=checkout_in.branch_id,
                    quantity=0.0
                )
                db.add(inventory)
            
            # Capture stock BEFORE deduction for the kardex
            prev_qty = inventory.quantity
            inventory.quantity -= item_in.quantity
            new_qty = inventory.quantity
            
            # Inventory Movement (kardex entry)
            movement = InventoryMovement(
                product_id=item_in.product_id,
                branch_id=checkout_in.branch_id,
                user_id=current_user.id,
                type=MovementType.OUT,
                quantity=-item_in.quantity,
                previous_stock=prev_qty,
                new_stock=new_qty,
                reference_id=str(sale.id),
                reason=f"Venta POS \u2014 {current_user.full_name or current_user.email}"
            )
            db.add(movement)
            
        # 3. Finalize Sale
        sale.subtotal = total_amount
        sale.total = total_amount
        
        # 4. Register Payment
        payment = Payment(
            sale_id=sale.id,
            method=checkout_in.payment_method,
            amount=checkout_in.amount_paid
        )
        db.add(payment)

        # 5. CRM: If CREDIT, register debt
        if sale.payment_method == "CREDIT" and sale.client_id:
            from app.models.client import Client
            from app.models.account_ledger import AccountLedger, LedgerType, PartnerType
            
            client_result = await db.execute(select(Client).where(Client.id == sale.client_id))
            client = client_result.scalar_one_or_none()
            if client:
                new_balance = client.current_balance + sale.total
                client.current_balance = new_balance
                db.add(client)
                
                ledger = AccountLedger(
                    partner_id=client.id,
                    partner_type=PartnerType.CLIENT,
                    type=LedgerType.CHARGE,
                    amount=sale.total,
                    balance_after=new_balance,
                    reference_id=str(sale.id),
                    description=f"Venta POS a crédito"
                )
                db.add(ledger)

        await db.commit()
        await db.refresh(sale)
        
        return {"success": True, "sale_id": sale.id, "total": sale.total, "change": checkout_in.amount_paid - sale.total}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
