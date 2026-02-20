from typing import Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.core import auth
from app.models.user import User
from app.core.permissions import PermissionChecker
from app.models.sale import Sale, SaleItem
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.category import Category

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
