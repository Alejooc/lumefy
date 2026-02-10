from typing import Any, List
from datetime import datetime, timedelta
from sqlalchemy import select, func, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.database import get_db
from app.core import auth
from app.models.user import User
from app.core.permissions import PermissionChecker
from app.models.sale import Sale, SaleItem
from app.models.inventory import Inventory
from app.models.product import Product
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

@router.get("/sales-summary", response_model=List[SalesSummary])
async def get_sales_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
    days: int = 7
) -> Any:
    """
    Get daily sales summary for the last N days.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Group sales by date
    # Note: 'date(Sale.created_at)' is database specific (PostgreSQL)
    query = (
        select(
            func.date(Sale.created_at).label("date"),
            func.sum(Sale.total).label("total"),
            func.count(Sale.id).label("count")
        )
        .where(
            Sale.company_id == current_user.company_id,
            Sale.created_at >= start_date
        )
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
    limit: int = 5
) -> Any:
    """
    Get top selling products by quantity.
    """
    query = (
        select(
            Product.name,
            func.sum(SaleItem.quantity).label("quantity"),
            func.sum(SaleItem.total).label("revenue")
        )
        .join(SaleItem.product)
        .join(SaleItem.sale)
        .where(Sale.company_id == current_user.company_id)
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
    current_user: User = Depends(PermissionChecker("view_reports"))
) -> Any:
    """
    Get total inventory value and status.
    """
    # Calculate total value (stock * price)
    # Join with Product to get price
    query = (
        select(
            func.sum(Inventory.quantity).label("total_items"),
            func.sum(Inventory.quantity * Product.price).label("total_value"),
            func.sum(
                case(
                    (Inventory.quantity <= Product.min_stock, 1),
                    else_=0
                )
            ).label("low_stock_items")
        )
        .join(Product, Inventory.product_id == Product.id)
        .where(Product.company_id == current_user.company_id)
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
