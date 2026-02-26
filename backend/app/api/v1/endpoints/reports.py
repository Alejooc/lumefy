from typing import Any, List, Optional
from datetime import date, datetime, time, timedelta
from sqlalchemy import select, func, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.core import auth
from app.models.user import User
from app.core.permissions import PermissionChecker
from app.models.sale import Sale, SaleItem, Payment
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.category import Category
from app.models.return_order import ReturnOrder, ReturnStatus
from app.models.pos_session import POSSession, POSSessionStatus

router = APIRouter()

class SalesSummary(BaseModel):
    date: str
    total: float
    count: int

class TopProduct(BaseModel):
    name: str
    quantity: float
    revenue: float

class InventoryValue(BaseModel):
    total_items: int
    total_value: float
    low_stock_items: int

class FinancialSummary(BaseModel):
    revenue: float
    cost: float
    profit: float
    margin: float

class InventoryTurnover(BaseModel):
    product_name: str
    stock: float
    sold_quantity: float
    turnover_rate: float

class SalesByCategory(BaseModel):
    category_name: str
    revenue: float

class DailyCloseSummary(BaseModel):
    date: str
    branch_id: Optional[str] = None
    sales_count: int
    gross_sales: float
    payments_cash: float
    payments_card: float
    payments_credit: float
    returns_count: int
    total_refunds: float
    net_sales: float
    sessions_opened_count: int
    sessions_closed_count: int
    opening_amount_total: float
    expected_amount_total: float
    counted_amount_total: float
    over_short_total: float
    open_sessions_now: int

class POSOpsTopCashier(BaseModel):
    user_id: str
    user_name: str
    sessions_closed: int
    sales_total: float
    cash_total: float
    card_total: float
    credit_total: float

class POSOperationsSummary(BaseModel):
    date: str
    branch_id: Optional[str] = None
    sessions_opened: int
    sessions_closed: int
    sessions_reopened: int
    sessions_open_now: int
    expected_total: float
    counted_total: float
    over_short_total: float
    alert_threshold: float
    alert_sessions_count: int
    payments_cash: float
    payments_card: float
    payments_credit: float
    top_cashiers: List[POSOpsTopCashier]


def _has_permission(user: User, permission: str) -> bool:
    if user.is_superuser:
        return True
    perms = (user.role.permissions if user.role else None) or {}
    if perms.get("all"):
        return True
    return bool(perms.get(permission))


def _reports_or_sales_manager(user: User = Depends(auth.get_current_user)) -> User:
    if _has_permission(user, "view_reports") or _has_permission(user, "manage_sales"):
        return user
    from fastapi import HTTPException, status
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Operation not permitted. Required permission: view_reports or manage_sales",
    )


def get_date_filter(model, start_date: Optional[datetime], end_date: Optional[datetime], days: int = 7):
    # Default to last 'days' if no dates provided
    if not start_date and not end_date:
        start_date = datetime.utcnow() - timedelta(days=days)
    conditions = []
    if start_date:
        # Convert to model compatible
        conditions.append(model.created_at >= start_date)
    if end_date:
        conditions.append(model.created_at <= end_date)
    return conditions


@router.get("/daily-close", response_model=DailyCloseSummary)
async def get_daily_close_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_reports_or_sales_manager),
    target_date: Optional[date] = None,
    branch_id: Optional[uuid.UUID] = None
) -> Any:
    """
    Daily close summary for operations: sales, payments, returns and POS sessions.
    """
    d = target_date or datetime.utcnow().date()
    # DB stores naive timestamps; use naive boundaries to avoid asyncpg tz mismatch errors.
    start_dt = datetime.combine(d, time.min)
    end_dt = datetime.combine(d, time.max)

    sale_conditions = [
        Sale.company_id == current_user.company_id,
        Sale.status != "CANCELLED",
        Sale.created_at >= start_dt,
        Sale.created_at <= end_dt,
    ]
    if branch_id:
        sale_conditions.append(Sale.branch_id == branch_id)

    sales_agg = await db.execute(
        select(
            func.count(Sale.id).label("sales_count"),
            func.coalesce(func.sum(Sale.total), 0.0).label("gross_sales"),
        ).where(*sale_conditions)
    )
    sales_row = sales_agg.one()

    payments_agg = await db.execute(
        select(
            func.coalesce(func.sum(Payment.amount).filter(Payment.method == "CASH"), 0.0).label("cash"),
            func.coalesce(func.sum(Payment.amount).filter(Payment.method == "CARD"), 0.0).label("card"),
            func.coalesce(func.sum(Payment.amount).filter(Payment.method == "CREDIT"), 0.0).label("credit"),
        )
        .join(Sale, Payment.sale_id == Sale.id)
        .where(*sale_conditions)
    )
    payments_row = payments_agg.one()

    return_conditions = [
        ReturnOrder.company_id == current_user.company_id,
        ReturnOrder.status == ReturnStatus.APPROVED,
        ReturnOrder.approved_at >= start_dt,
        ReturnOrder.approved_at <= end_dt,
    ]
    if branch_id:
        return_conditions.append(Sale.branch_id == branch_id)

    returns_agg = await db.execute(
        select(
            func.count(ReturnOrder.id).label("returns_count"),
            func.coalesce(func.sum(ReturnOrder.total_refund), 0.0).label("total_refunds"),
        )
        .join(Sale, ReturnOrder.sale_id == Sale.id)
        .where(*return_conditions)
    )
    returns_row = returns_agg.one()

    session_base_conditions = [
        POSSession.company_id == current_user.company_id,
    ]
    if branch_id:
        session_base_conditions.append(POSSession.branch_id == branch_id)

    sessions_opened_agg = await db.execute(
        select(
            func.count(POSSession.id).label("sessions_opened_count"),
            func.coalesce(func.sum(POSSession.opening_amount), 0.0).label("opening_amount_total"),
        ).where(
            *session_base_conditions,
            POSSession.opened_at >= start_dt,
            POSSession.opened_at <= end_dt,
        )
    )
    sessions_opened_row = sessions_opened_agg.one()

    sessions_closed_agg = await db.execute(
        select(
            func.count(POSSession.id).label("sessions_closed_count"),
            func.coalesce(func.sum(POSSession.expected_amount), 0.0).label("expected_amount_total"),
            func.coalesce(func.sum(POSSession.counted_amount), 0.0).label("counted_amount_total"),
            func.coalesce(func.sum(POSSession.over_short), 0.0).label("over_short_total"),
        ).where(
            *session_base_conditions,
            POSSession.status == POSSessionStatus.CLOSED,
            POSSession.closed_at >= start_dt,
            POSSession.closed_at <= end_dt,
        )
    )
    sessions_closed_row = sessions_closed_agg.one()

    open_now_agg = await db.execute(
        select(func.count(POSSession.id).label("open_sessions_now")).where(
            *session_base_conditions,
            POSSession.status == POSSessionStatus.OPEN,
        )
    )
    open_now_row = open_now_agg.one()

    gross_sales = float(sales_row.gross_sales or 0.0)
    total_refunds = float(returns_row.total_refunds or 0.0)

    return DailyCloseSummary(
        date=d.isoformat(),
        branch_id=str(branch_id) if branch_id else None,
        sales_count=int(sales_row.sales_count or 0),
        gross_sales=gross_sales,
        payments_cash=float(payments_row.cash or 0.0),
        payments_card=float(payments_row.card or 0.0),
        payments_credit=float(payments_row.credit or 0.0),
        returns_count=int(returns_row.returns_count or 0),
        total_refunds=total_refunds,
        net_sales=gross_sales - total_refunds,
        sessions_opened_count=int(sessions_opened_row.sessions_opened_count or 0),
        sessions_closed_count=int(sessions_closed_row.sessions_closed_count or 0),
        opening_amount_total=float(sessions_opened_row.opening_amount_total or 0.0),
        expected_amount_total=float(sessions_closed_row.expected_amount_total or 0.0),
        counted_amount_total=float(sessions_closed_row.counted_amount_total or 0.0),
        over_short_total=float(sessions_closed_row.over_short_total or 0.0),
        open_sessions_now=int(open_now_row.open_sessions_now or 0),
    )


@router.get("/pos-operations", response_model=POSOperationsSummary)
async def get_pos_operations_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_reports_or_sales_manager),
    target_date: Optional[date] = None,
    branch_id: Optional[uuid.UUID] = None,
    alert_threshold: float = 20.0,
) -> Any:
    """
    Consolidated operational report for POS sessions (day-level):
    opened/closed/reopened/open-now, cash over/short and top cashiers.
    """
    d = target_date or datetime.utcnow().date()
    start_dt = datetime.combine(d, time.min)
    end_dt = datetime.combine(d, time.max)
    threshold = float(alert_threshold or 20.0)

    session_base_conditions = [POSSession.company_id == current_user.company_id]
    sale_conditions = [
        Sale.company_id == current_user.company_id,
        Sale.status != "CANCELLED",
        Sale.created_at >= start_dt,
        Sale.created_at <= end_dt,
    ]
    if branch_id:
        session_base_conditions.append(POSSession.branch_id == branch_id)
        sale_conditions.append(Sale.branch_id == branch_id)

    opened_row = (
        await db.execute(
            select(func.count(POSSession.id)).where(
                *session_base_conditions,
                POSSession.opened_at >= start_dt,
                POSSession.opened_at <= end_dt,
            )
        )
    ).one()

    closed_row = (
        await db.execute(
            select(
                func.count(POSSession.id).label("sessions_closed"),
                func.coalesce(func.sum(POSSession.expected_amount), 0.0).label("expected_total"),
                func.coalesce(func.sum(POSSession.counted_amount), 0.0).label("counted_total"),
                func.coalesce(func.sum(POSSession.over_short), 0.0).label("over_short_total"),
            ).where(
                *session_base_conditions,
                POSSession.status == POSSessionStatus.CLOSED,
                POSSession.closed_at >= start_dt,
                POSSession.closed_at <= end_dt,
            )
        )
    ).one()

    reopened_row = (
        await db.execute(
            select(func.count(POSSession.id)).where(
                *session_base_conditions,
                POSSession.closing_note.ilike("%[POS_REOPEN_AUDIT]%"),
                POSSession.updated_at >= start_dt,
                POSSession.updated_at <= end_dt,
            )
        )
    ).one()

    open_now_row = (
        await db.execute(
            select(func.count(POSSession.id)).where(
                *session_base_conditions,
                POSSession.status == POSSessionStatus.OPEN,
            )
        )
    ).one()

    alerts_row = (
        await db.execute(
            select(func.count(POSSession.id)).where(
                *session_base_conditions,
                POSSession.status == POSSessionStatus.CLOSED,
                POSSession.closed_at >= start_dt,
                POSSession.closed_at <= end_dt,
                func.abs(POSSession.over_short) >= threshold,
            )
        )
    ).one()

    payments_row = (
        await db.execute(
            select(
                func.coalesce(func.sum(Payment.amount).filter(Payment.method == "CASH"), 0.0).label("cash"),
                func.coalesce(func.sum(Payment.amount).filter(Payment.method == "CARD"), 0.0).label("card"),
                func.coalesce(func.sum(Payment.amount).filter(Payment.method == "CREDIT"), 0.0).label("credit"),
            )
            .join(Sale, Payment.sale_id == Sale.id)
            .where(*sale_conditions)
        )
    ).one()

    top_cashiers_rows = (
        await db.execute(
            select(
                User.id.label("user_id"),
                func.coalesce(User.full_name, User.email).label("user_name"),
                func.count(func.distinct(POSSession.id)).label("sessions_closed"),
                func.coalesce(func.sum(Payment.amount), 0.0).label("sales_total"),
                func.coalesce(func.sum(Payment.amount).filter(Payment.method == "CASH"), 0.0).label("cash_total"),
                func.coalesce(func.sum(Payment.amount).filter(Payment.method == "CARD"), 0.0).label("card_total"),
                func.coalesce(func.sum(Payment.amount).filter(Payment.method == "CREDIT"), 0.0).label("credit_total"),
            )
            .join(POSSession, POSSession.user_id == User.id)
            .join(Sale, Sale.pos_session_id == POSSession.id)
            .join(Payment, Payment.sale_id == Sale.id)
            .where(
                User.company_id == current_user.company_id,
                POSSession.company_id == current_user.company_id,
                POSSession.status == POSSessionStatus.CLOSED,
                POSSession.closed_at >= start_dt,
                POSSession.closed_at <= end_dt,
                *([POSSession.branch_id == branch_id] if branch_id else []),
                Sale.status != "CANCELLED",
                Sale.created_at >= start_dt,
                Sale.created_at <= end_dt,
            )
            .group_by(User.id, User.full_name, User.email)
            .order_by(desc("sales_total"))
            .limit(10)
        )
    ).all()

    top_cashiers = [
        POSOpsTopCashier(
            user_id=str(row.user_id),
            user_name=row.user_name or "-",
            sessions_closed=int(row.sessions_closed or 0),
            sales_total=float(row.sales_total or 0.0),
            cash_total=float(row.cash_total or 0.0),
            card_total=float(row.card_total or 0.0),
            credit_total=float(row.credit_total or 0.0),
        )
        for row in top_cashiers_rows
    ]

    return POSOperationsSummary(
        date=d.isoformat(),
        branch_id=str(branch_id) if branch_id else None,
        sessions_opened=int(opened_row[0] or 0),
        sessions_closed=int(closed_row.sessions_closed or 0),
        sessions_reopened=int(reopened_row[0] or 0),
        sessions_open_now=int(open_now_row[0] or 0),
        expected_total=float(closed_row.expected_total or 0.0),
        counted_total=float(closed_row.counted_total or 0.0),
        over_short_total=float(closed_row.over_short_total or 0.0),
        alert_threshold=threshold,
        alert_sessions_count=int(alerts_row[0] or 0),
        payments_cash=float(payments_row.cash or 0.0),
        payments_card=float(payments_row.card or 0.0),
        payments_credit=float(payments_row.credit or 0.0),
        top_cashiers=top_cashiers,
    )


@router.get("/sales-summary", response_model=List[SalesSummary])
async def get_sales_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
    days: int = 7,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    branch_id: Optional[uuid.UUID] = None
) -> Any:
    """Get daily sales summary."""
    conditions = get_date_filter(Sale, start_date, end_date, days)
    conditions.append(Sale.company_id == current_user.company_id)
    # Only completed or delivered? Existing code counted all sales. We'll stick to not CANCELLED
    conditions.append(Sale.status != "CANCELLED")
    
    if branch_id:
        conditions.append(Sale.branch_id == branch_id)
        
    query = (
        select(
            func.date(Sale.created_at).label("date"),
            func.sum(Sale.total).label("total"),
            func.count(Sale.id).label("count")
        )
        .where(*conditions)
        .group_by(func.date(Sale.created_at))
        .order_by(func.date(Sale.created_at))
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    return [
        SalesSummary(
            date=str(row.date),
            total=float(row.total or 0),
            count=int(row.count or 0)
        )
        for row in rows
    ]


@router.get("/top-products", response_model=List[TopProduct])
async def get_top_products(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
    limit: int = 5,
    days: int = 30,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    branch_id: Optional[uuid.UUID] = None
) -> Any:
    """Get top selling products by quantity."""
    conditions = get_date_filter(Sale, start_date, end_date, days)
    conditions.append(Sale.company_id == current_user.company_id)
    conditions.append(Sale.status != "CANCELLED")
    
    if branch_id:
        conditions.append(Sale.branch_id == branch_id)
        
    query = (
        select(
            Product.name,
            func.sum(SaleItem.quantity).label("quantity"),
            func.sum(SaleItem.total).label("revenue")
        )
        .join(SaleItem.product)
        .join(SaleItem.sale)
        .where(*conditions)
        .group_by(Product.id, Product.name)
        .order_by(desc("quantity"))
        .limit(limit)
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    return [
        TopProduct(
            name=row.name,
            quantity=float(row.quantity or 0),
            revenue=float(row.revenue or 0)
        )
        for row in rows
    ]


@router.get("/inventory-value", response_model=InventoryValue)
async def get_inventory_value(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
    branch_id: Optional[uuid.UUID] = None
) -> Any:
    """Get total inventory value and status."""
    conditions = [Product.company_id == current_user.company_id]
    if branch_id:
        conditions.append(Inventory.branch_id == branch_id)
        
    query = (
        select(
            func.sum(Inventory.quantity).label("total_items"),
            func.sum(Inventory.quantity * func.coalesce(Product.cost, Product.price, 0.0)).label("total_value"),
            func.sum(
                case(
                    (Inventory.quantity <= Product.min_stock, 1),
                    else_=0
                )
            ).label("low_stock_items")
        )
        .join(Product, Inventory.product_id == Product.id)
        .where(*conditions)
    )
    
    result = await db.execute(query)
    row = result.first()
    
    if not row:
        return InventoryValue(total_items=0, total_value=0, low_stock_items=0)
        
    return InventoryValue(
        total_items=int(row.total_items or 0),
        total_value=float(row.total_value or 0),
        low_stock_items=int(row.low_stock_items or 0)
    )


@router.get("/financial-summary", response_model=FinancialSummary)
async def get_financial_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
    days: int = 30,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    branch_id: Optional[uuid.UUID] = None
) -> Any:
    """Get revenue, costs, and profit."""
    conditions = get_date_filter(Sale, start_date, end_date, days)
    conditions.append(Sale.company_id == current_user.company_id)
    conditions.append(Sale.status != "CANCELLED")
    
    if branch_id:
        conditions.append(Sale.branch_id == branch_id)
        
    query = (
        select(
            func.sum(SaleItem.total).label("revenue"),
            func.sum(SaleItem.quantity * func.coalesce(Product.cost, 0)).label("cost")
        )
        .join(SaleItem.sale)
        .join(SaleItem.product)
        .where(*conditions)
    )
    
    result = await db.execute(query)
    row = result.first()
    
    revenue = float(row.revenue or 0)
    cost = float(row.cost or 0)
    profit = revenue - cost
    margin = (profit / revenue * 100) if revenue > 0 else 0
    
    return FinancialSummary(
        revenue=revenue,
        cost=cost,
        profit=profit,
        margin=margin
    )


@router.get("/inventory-turnover", response_model=List[InventoryTurnover])
async def get_inventory_turnover(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
    days: int = 30,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    branch_id: Optional[uuid.UUID] = None,
    limit: int = 10,
    sort_by: str = "highest"
) -> Any:
    """Get products with highest/lowest turnover (sales vs stock)."""
    conditions = get_date_filter(Sale, start_date, end_date, days)
    conditions.append(Sale.company_id == current_user.company_id)
    conditions.append(Sale.status != "CANCELLED")
    
    if branch_id:
        conditions.append(Sale.branch_id == branch_id)
        
    sales_subq = (
        select(
            SaleItem.product_id,
            func.sum(SaleItem.quantity).label("sold_quantity")
        )
        .join(SaleItem.sale)
        .where(*conditions)
        .group_by(SaleItem.product_id)
        .subquery()
    )
    
    inv_conditions = [Inventory.company_id == current_user.company_id]
    if branch_id:
        inv_conditions.append(Inventory.branch_id == branch_id)
        
    inv_subq = (
        select(
            Inventory.product_id,
            func.sum(Inventory.quantity).label("total_stock")
        )
        .where(*inv_conditions)
        .group_by(Inventory.product_id)
        .subquery()
    )
    
    query = (
        select(
            Product.name,
            func.coalesce(inv_subq.c.total_stock, 0).label("stock"),
            func.coalesce(sales_subq.c.sold_quantity, 0).label("sold_quantity")
        )
        .outerjoin(inv_subq, Product.id == inv_subq.c.product_id)
        .outerjoin(sales_subq, Product.id == sales_subq.c.product_id)
        .where(Product.company_id == current_user.company_id)
    )
    
    # We want to ignore products with absolutely 0 stock and 0 sales in the period if we sort
    query = query.where(func.coalesce(inv_subq.c.total_stock, 0) + func.coalesce(sales_subq.c.sold_quantity, 0) > 0)
    
    if sort_by == "highest":
        query = query.order_by(desc(func.coalesce(sales_subq.c.sold_quantity, 0))).limit(limit)
    else: 
        query = query.order_by(func.coalesce(sales_subq.c.sold_quantity, 0), desc(func.coalesce(inv_subq.c.total_stock, 0))).limit(limit)

    result = await db.execute(query)
    rows = result.all()
    
    response = []
    for r in rows:
        stock = float(r.stock or 0)
        sold = float(r.sold_quantity or 0)
        turnover = (sold / stock) if stock > 0 else sold
        response.append(InventoryTurnover(
            product_name=r.name,
            stock=stock,
            sold_quantity=sold,
            turnover_rate=turnover
        ))
    return response


@router.get("/sales-by-category", response_model=List[SalesByCategory])
async def get_sales_by_category(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
    days: int = 30,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    branch_id: Optional[uuid.UUID] = None
) -> Any:
    """Get revenue grouped by category."""
    conditions = get_date_filter(Sale, start_date, end_date, days)
    conditions.append(Sale.company_id == current_user.company_id)
    conditions.append(Sale.status != "CANCELLED")
    
    if branch_id:
        conditions.append(Sale.branch_id == branch_id)
        
    query = (
        select(
            func.coalesce(Category.name, "Sin Categoría").label("category_name"),
            func.sum(SaleItem.total).label("revenue")
        )
        .join(SaleItem.sale)
        .join(SaleItem.product)
        .outerjoin(Product.category)
        .where(*conditions)
        .group_by(Category.id, Category.name)
        .order_by(desc("revenue"))
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    return [
        SalesByCategory(category_name=row.category_name, revenue=float(row.revenue or 0))
        for row in rows
    ]
