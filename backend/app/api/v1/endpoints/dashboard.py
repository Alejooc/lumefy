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
    current_user: User = Depends(PermissionChecker("view_dashboard")), # Or just authenticated
) -> Any:
    """
    Get statistics for the dashboard.
    """
    
    # 1. Card Metrics
    # Total Users (Customers?) - Let's count Clients? Or Users? 
    # Dashboard says "Total Users". Let's count Users in the Company.
    
    # Total Users
    q_users = select(func.count(User.id)).where(User.company_id == current_user.company_id)
    res_users = await db.execute(q_users)
    total_users_count = res_users.scalar() or 0
    
    # Total Products
    q_products = select(func.count(Product.id)).where(Product.company_id == current_user.company_id)
    res_products = await db.execute(q_products)
    total_products_count = res_products.scalar() or 0
    
    # Total Orders (Sales)
    q_sales_count = select(func.count(Sale.id)).where(Sale.company_id == current_user.company_id)
    res_sales_count = await db.execute(q_sales_count)
    total_orders_count = res_sales_count.scalar() or 0
    
    # Total Revenue (Sales Total) - Only PAID or COMPLETED? Or all? 
    # Let's sum all mostly positive statuses?
    # For now sum all.
    q_revenue = select(func.sum(Sale.total)).where(
        Sale.company_id == current_user.company_id,
        Sale.status.notin_([SaleStatus.DRAFT, SaleStatus.QUOTE, SaleStatus.CANCELLED])
    )
    res_revenue = await db.execute(q_revenue)
    total_revenue = res_revenue.scalar() or 0.0
    
    # Construct Cards
    # Construct Cards
    cards = [
        {
            "title": "Usuarios",
            "amount": str(total_users_count),
            "background": "bg-light-primary",
            "border": "border-primary",
            "icon": "rise",
            "percentage": "100%", # Placeholder
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

    # 2. Recent Orders (Sales)
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
    
    res_recent = await db.execute(q_recent_orders)
    recent_sales = res_recent.scalars().all()
    
    recent_orders_data = []
    for sale in recent_sales:
        # Get first product name or "Multiple Items"
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
            "id": str(sale.id)[:8], # Truncated ID
            "name": product_name,
            "status": sale.status.value,
            "status_type": status_color,
            "quantity": sum(i.quantity for i in sale.items) if sale.items else 0,
            "amount": f"${sale.total:,.2f}"
        })
        
    # 3. Transaction History (Just recent sales for now)
    # Re-use recent sales but format differently
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
    
    # 4a. Income Overview (Weekly Sales - Last 7 days)
    # Get sales grouped by day
    today = datetime.now().date()
    start_date = today - timedelta(days=6)
    
    # We need to fill zeros for days with no sales.
    # Python aggregation is safer/easier for DB agnostic (though we know it's PG).
    
    q_weekly = select(Sale).where(
        Sale.company_id == current_user.company_id,
        Sale.created_at >= start_date,
        Sale.status.notin_([SaleStatus.DRAFT, SaleStatus.QUOTE, SaleStatus.CANCELLED])
    )
    res_weekly = await db.execute(q_weekly)
    weekly_sales_list = res_weekly.scalars().all()
    
    weekly_map = { (start_date + timedelta(days=i)): 0.0 for i in range(7) }
    
    for sale in weekly_sales_list:
        d = sale.created_at.date()
        if d in weekly_map:
            weekly_map[d] += sale.total
            
    # Prepare chart structure
    days_map = {
        "Mon": "Lun", "Tue": "Mar", "Wed": "Mie", "Thu": "Jue", "Fri": "Vie", "Sat": "Sab", "Sun": "Dom"
    }
    days_labels = [days_map.get(d.strftime("%a"), d.strftime("%a")) for d in weekly_map.keys()]
    weekly_values = list(weekly_map.values())
    
    income_overview_data = {
        "categories": days_labels,
        "series": [{"name": "Ingresos", "data": weekly_values}]
    }

    # 4b. Monthly Sales (Last 12 months? Or Current Year?)
    # Let's do Current Year Jan-Dec
    current_year = today.year
    start_year = datetime(current_year, 1, 1)
    
    q_monthly = select(Sale).where(
        Sale.company_id == current_user.company_id,
        Sale.created_at >= start_year,
        Sale.status.notin_([SaleStatus.DRAFT, SaleStatus.QUOTE, SaleStatus.CANCELLED])
    )
    res_monthly = await db.execute(q_monthly)
    monthly_sales_list = res_monthly.scalars().all()
    
    # Initialize 12 months
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
            # Placeholder for 'Sessions' or something else? Just duplicate for now or remove.
            # {"name": "Profit", "data": [v * 0.2 for v in monthly_values]} 
        ]
    }
    
    # 4c. Sales Report (Last 6 months?)
    # Re-use monthly data but last 6
    sales_report_data = {
         "categories": monthly_labels[:6], # Just first 6 for demo
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
