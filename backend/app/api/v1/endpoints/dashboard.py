from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core.database import get_db
from app.models.user import User
from app.models.product import Product
from app.models.sale import Sale, SaleStatus, SaleItem
from app.core.permissions import PermissionChecker
from app.schemas import dashboard as schemas

router = APIRouter()

@router.get("/", response_model=schemas.DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_dashboard")),
    date_from: str = None,
    date_to: str = None,
    branch_id: str = None,
) -> Any:
    """
    Get statistics for the dashboard.
    Optional filters: date_from, date_to (ISO format), branch_id (UUID).
    """
    
    # Parse date filters
    parsed_date_from = None
    parsed_date_to = None
    if date_from:
        try:
            parsed_date_from = datetime.fromisoformat(date_from)
        except ValueError:
            pass
    if date_to:
        try:
            parsed_date_to = datetime.fromisoformat(date_to)
            # Include the full end day
            if parsed_date_to.hour == 0 and parsed_date_to.minute == 0:
                parsed_date_to = parsed_date_to + timedelta(days=1) - timedelta(seconds=1)
        except ValueError:
            pass
    
    # Helper to apply common sale filters
    def apply_sale_filters(query):
        if parsed_date_from:
            query = query.where(Sale.created_at >= parsed_date_from)
        if parsed_date_to:
            query = query.where(Sale.created_at <= parsed_date_to)
        if branch_id:
            query = query.where(Sale.branch_id == branch_id)
        return query

    # 1. Card Metrics
    # Total Users (not filtered by date/branch as it's a count)
    q_users = select(func.count(User.id)).where(User.company_id == current_user.company_id)
    res_users = await db.execute(q_users)
    total_users_count = res_users.scalar() or 0
    
    # Total Products (not filtered by date/branch)
    q_products = select(func.count(Product.id)).where(Product.company_id == current_user.company_id)
    res_products = await db.execute(q_products)
    total_products_count = res_products.scalar() or 0
    
    # Total Orders (Sales) - filtered
    q_sales_count = select(func.count(Sale.id)).where(Sale.company_id == current_user.company_id)
    q_sales_count = apply_sale_filters(q_sales_count)
    res_sales_count = await db.execute(q_sales_count)
    total_orders_count = res_sales_count.scalar() or 0
    
    # Total Revenue - filtered
    q_revenue = select(func.sum(Sale.total)).where(
        Sale.company_id == current_user.company_id,
        Sale.status.notin_([SaleStatus.DRAFT, SaleStatus.QUOTE, SaleStatus.CANCELLED])
    )
    q_revenue = apply_sale_filters(q_revenue)
    res_revenue = await db.execute(q_revenue)
    total_revenue = res_revenue.scalar() or 0.0
    
    # Construct Cards
    cards = [
        {
            "title": "Usuarios",
            "amount": str(total_users_count),
            "background": "bg-light-primary",
            "border": "border-primary",
            "icon": "rise",
            "percentage": "100%",
            "color": "text-primary",
            "number": str(total_users_count) 
        },
        {
            "title": "Productos",
            "amount": str(total_products_count),
            "background": "bg-light-primary", 
            "border": "border-primary",
            "icon": "rise",
            "percentage": "-",
            "color": "text-primary",
            "number": str(total_products_count)
        },
        {
            "title": "Pedidos",
            "amount": str(total_orders_count),
            "background": "bg-light-warning",
            "border": "border-warning",
            "icon": "rise",
            "percentage": "-",
            "color": "text-warning",
            "number": str(total_orders_count)
        },
        {
            "title": "Ingresos",
            "amount": f"${total_revenue:,.2f}",
            "background": "bg-light-success",
            "border": "border-success",
            "icon": "rise",
            "percentage": "-",
            "color": "text-success",
            "number": f"${total_revenue:,.2f}"
        },
    ]

    # 2. Recent Orders (Sales) - filtered
    q_recent_orders = select(Sale).options(
        selectinload(Sale.items).selectinload(SaleItem.product).options(
            selectinload(Product.images),
            selectinload(Product.variants),
            selectinload(Product.brand),
            selectinload(Product.unit_of_measure),
            selectinload(Product.purchase_uom),
            selectinload(Product.category)
        )
    ).where(
        Sale.company_id == current_user.company_id
    ).order_by(Sale.created_at.desc()).limit(5)
    q_recent_orders = apply_sale_filters(q_recent_orders)
    
    res_recent = await db.execute(q_recent_orders)
    recent_sales = res_recent.scalars().all()
    
    recent_orders_data = []
    for sale in recent_sales:
        if sale.items and len(sale.items) > 0:
            product_name = sale.items[0].product.name if sale.items[0].product else "Producto Desconocido"
            if len(sale.items) > 1:
                product_name += f" (+{len(sale.items)-1} más)"
        else:
            product_name = "Sin items"
            
        status_color = "text-warning"
        if sale.status == SaleStatus.COMPLETED:
            status_color = "text-success"
        elif sale.status == SaleStatus.CANCELLED:
            status_color = "text-danger"
            
        recent_orders_data.append({
            "id": str(sale.id)[:8],
            "name": product_name,
            "status": sale.status.value,
            "status_type": status_color,
            "quantity": sum(i.quantity for i in sale.items) if sale.items else 0,
            "amount": f"${sale.total:,.2f}"
        })
        
    # 3. Transactions
    transactions_data = []
    for sale in recent_sales[:3]:
        transactions_data.append({
            "background": "text-success bg-light-success" if sale.status == SaleStatus.COMPLETED else "text-warning bg-light-warning",
            "icon": "gift" if sale.status == SaleStatus.COMPLETED else "message",
            "title": f"Pedido #{str(sale.id)[:6]}",
            "time": sale.created_at.strftime("%d %b, %H:%M"),
            "amount": f"+ ${sale.total:,.2f}",
            "percentage": "-"
        })
        
    # 4. Charts Data
    
    # 4a. Income Overview (Weekly Sales - Last 7 days or filtered range)
    today = datetime.now().date()

    if parsed_date_from and parsed_date_to:
        chart_start = parsed_date_from.date() if hasattr(parsed_date_from, 'date') else parsed_date_from
        chart_end = parsed_date_to.date() if hasattr(parsed_date_to, 'date') else parsed_date_to
    else:
        chart_start = today - timedelta(days=6)
        chart_end = today

    q_weekly = select(Sale).where(
        Sale.company_id == current_user.company_id,
        Sale.created_at >= chart_start,
        Sale.created_at <= chart_end + timedelta(days=1),
        Sale.status.notin_([SaleStatus.DRAFT, SaleStatus.QUOTE, SaleStatus.CANCELLED])
    )
    if branch_id:
        q_weekly = q_weekly.where(Sale.branch_id == branch_id)
    res_weekly = await db.execute(q_weekly)
    weekly_sales_list = res_weekly.scalars().all()
    
    num_days = (chart_end - chart_start).days + 1
    weekly_map = { (chart_start + timedelta(days=i)): 0.0 for i in range(num_days) }
    
    for sale in weekly_sales_list:
        d = sale.created_at.date()
        if d in weekly_map:
            weekly_map[d] += sale.total
            
    days_map = {
        "Mon": "Lun", "Tue": "Mar", "Wed": "Mie", "Thu": "Jue", "Fri": "Vie", "Sat": "Sab", "Sun": "Dom"
    }
    
    if num_days <= 7:
        days_labels = [days_map.get(d.strftime("%a"), d.strftime("%a")) for d in weekly_map.keys()]
    else:
        days_labels = [d.strftime("%d/%m") for d in weekly_map.keys()]
    weekly_values = list(weekly_map.values())
    
    income_overview_data = {
        "categories": days_labels,
        "series": [{"name": "Ingresos", "data": weekly_values}]
    }

    # 4b. Monthly Sales (Current Year) - filtered
    current_year = today.year
    start_year = datetime(current_year, 1, 1)
    
    q_monthly = select(Sale).where(
        Sale.company_id == current_user.company_id,
        Sale.created_at >= start_year,
        Sale.status.notin_([SaleStatus.DRAFT, SaleStatus.QUOTE, SaleStatus.CANCELLED])
    )
    if branch_id:
        q_monthly = q_monthly.where(Sale.branch_id == branch_id)
    res_monthly = await db.execute(q_monthly)
    monthly_sales_list = res_monthly.scalars().all()
    
    monthly_map = { i: 0.0 for i in range(1, 13) }
    for sale in monthly_sales_list:
        m = sale.created_at.month
        monthly_map[m] += sale.total
        
    monthly_values = [monthly_map[i] for i in range(1, 13)]
    monthly_labels = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    
    monthly_sales_chart = {
        "categories": monthly_labels,
        "series": [
            {"name": "Ingresos", "data": monthly_values},
        ]
    }
    
    # 4c. Sales Report
    sales_report_data = {
         "categories": monthly_labels[:6],
         "series": [
             {"name": "Ingresos", "data": monthly_values[:6]},
             {"name": "Beneficio", "data": [v * 0.3 for v in monthly_values[:6]]}
         ]
    }
    
    return {
        "cards": cards,
        "recent_orders": recent_orders_data,
        "transactions": transactions_data,
        "monthly_sales": monthly_sales_chart,
        "income_overview": income_overview_data,
        "sales_report": sales_report_data
    }


@router.get("/health", response_model=schemas.DashboardHealth)
async def get_dashboard_health(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    _ = current_user
    checked_at = datetime.utcnow()

    db_ok = False
    db_message = None
    current_revision = None

    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:  # pragma: no cover
        db_message = str(exc)

    if db_ok:
        try:
            revision_row = await db.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            current_revision = revision_row.scalar_one_or_none()
        except Exception as exc:  # pragma: no cover
            db_message = str(exc)

    expected_head = None
    try:
        backend_root = Path(__file__).resolve().parents[4]
        alembic_ini = backend_root / "alembic.ini"
        if alembic_ini.exists():
            config = Config(str(alembic_ini))
            config.set_main_option("script_location", str(backend_root / "alembic"))
            script = ScriptDirectory.from_config(config)
            expected_head = script.get_current_head()
    except Exception:
        expected_head = None

    migration_up_to_date = None
    if current_revision and expected_head:
        migration_up_to_date = current_revision == expected_head

    return {
        "backend_ok": True,
        "db_ok": db_ok,
        "db_message": db_message,
        "current_revision": current_revision,
        "expected_head": expected_head,
        "migration_up_to_date": migration_up_to_date,
        "checked_at": checked_at,
    }
