from typing import Any, List, Dict
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, cast, String, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import auth
from app.core.database import get_db
from app.models.product import Product
from app.models.client import Client
from app.models.user import User
from app.models.sale import Sale
from app.models.company import Company
from uuid import UUID

router = APIRouter()

@router.get("", response_model=Dict[str, List[Any]])
async def global_search(
    q: str = Query(..., min_length=2, description="Search term"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Global search across multiple entities (Products, Clients, Sales, Users).
    Scoped to the current user's company unless Super Admin (though UI context usually dictates scope).
    For now, we scope everything to the tenant/company for safety.
    """
    search_term = f"%{q}%"
    results = {
        "products": [],
        "clients": [],
        "sales": [],
        "users": []
    }

    # 1. Search Products (Name or SKU)
    # ----------------------------------------------------------------
    query_prod = select(Product).where(
        Product.company_id == current_user.company_id,
        or_(
            Product.name.ilike(search_term),
            Product.sku.ilike(search_term)
        )
    ).limit(5)
    
    products = await db.execute(query_prod)
    for p in products.scalars().all():
        results["products"].append({
            "id": p.id,
            "title": p.name,
            "subtitle": f"SKU: {p.sku} | ${p.price}",
            "url": f"/products/edit/{p.id}",
            "icon": "shopping-cart"
        })

    # 2. Search Clients (Name, Email, Phone)
    # ----------------------------------------------------------------
    query_client = select(Client).where(
        Client.company_id == current_user.company_id,
        or_(
            Client.full_name.ilike(search_term),
            Client.email.ilike(search_term),
            Client.phone.ilike(search_term)
        )
    ).limit(5)

    clients = await db.execute(query_client)
    for c in clients.scalars().all():
        results["clients"].append({
            "id": c.id,
            "title": c.full_name,
            "subtitle": c.email,
            "url": f"/clients/edit/{c.id}",
            "icon": "user"
        })

    # 3. Search Sales/Orders (ID or Status?)
    # ----------------------------------------------------------------
    # Casting UUID to string for search might be SLOW on large datasets, 
    # but for typical tenant sizes it's acceptable for a convenience feature.
    # Searching exact ID is better if q is a UUID, but q is partial text usually.
    # We'll search ID cast to text.
    
    query_sale = select(Sale).where(
        Sale.company_id == current_user.company_id,
        cast(Sale.id, String).ilike(search_term)
    ).limit(5)

    sales = await db.execute(query_sale)
    for s in sales.scalars().all():
        results["sales"].append({
            "id": s.id,
            "title": f"Pedido #{str(s.id)[:8]}...", # Short ID for display
            "subtitle": f"Total: ${s.total} | {s.status}",
            "url": f"/sales/detail/{s.id}",
            "icon": "file-text"
        })

    # 4. Search Users (Name, Email)
    # ----------------------------------------------------------------
    query_user = select(User).where(
        User.company_id == current_user.company_id,
        or_(
            User.full_name.ilike(search_term),
            User.email.ilike(search_term)
        )
    ).limit(5)

    users = await db.execute(query_user)
    for u in users.scalars().all():
        results["users"].append({
            "id": u.id,
            "title": u.full_name,
            "subtitle": u.email,
            "url": f"/users/edit/{u.id}",
            "icon": "team"
        })

    return results
