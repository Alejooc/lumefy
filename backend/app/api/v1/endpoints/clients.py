from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import auth
from app.core.permissions import PermissionChecker
from app.core.database import get_db
from app.models.client import Client
from app.models.user import User
from app.models.client_activity import ClientActivity, ActivityType
from app.models.sale import Sale
from app.models.account_ledger import AccountLedger, PartnerType, LedgerType
from app.schemas import client as schemas
from app.schemas import account_ledger as account_ledger_schemas
from app.schemas.sale import ClientSalesResponse
from sqlalchemy import func, desc, and_
from sqlalchemy.orm import selectinload

router = APIRouter()

@router.get("/", response_model=List[schemas.Client])
async def read_clients(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    q: str = Query(None, min_length=1),
    status: str = Query(None),
    current_user: User = Depends(PermissionChecker("manage_clients")),
) -> Any:
    """
    Retrieve clients.
    """
    query = select(Client).where(Client.company_id == current_user.company_id)
    
    if q:
        query = query.where(
            or_(
                Client.name.ilike(f"%{q}%"),
                Client.tax_id.ilike(f"%{q}%"),
                Client.email.ilike(f"%{q}%")
            )
        )
        
    if status:
        query = query.where(Client.status == status)
        
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/export")
async def export_clients(
    db: AsyncSession = Depends(get_db),
    format: str = "excel",
    current_user: User = Depends(PermissionChecker("manage_clients")),
) -> Any:
    """Export clients to Excel or CSV."""
    from app.services.export_service import ExportService

    query = select(Client).where(Client.company_id == current_user.company_id)
    result = await db.execute(query)
    clients = result.scalars().all()

    columns = {
        "name": "Nombre",
        "tax_id": "RUC/NIT",
        "email": "Email",
        "phone": "Teléfono",
        "address": "Dirección",
        "city": "Ciudad",
        "created_at": "Fecha Registro",
    }

    rows = []
    for c in clients:
        rows.append({
            "name": c.name or "",
            "tax_id": c.tax_id or "",
            "email": c.email or "",
            "phone": c.phone or "",
            "address": c.address or "",
            "city": getattr(c, "city", "") or "",
            "created_at": c.created_at.strftime("%Y-%m-%d") if c.created_at else "",
        })

    if format == "csv":
        return ExportService.to_csv_response(rows, columns, filename="clientes")
    return ExportService.to_excel_response(rows, columns, filename="clientes")

@router.post("/", response_model=schemas.Client)
async def create_client(
    *,
    db: AsyncSession = Depends(get_db),
    client_in: schemas.ClientCreate,
    current_user: User = Depends(PermissionChecker("manage_clients")),
) -> Any:
    """
    Create new client.
    """
    client = Client(
        **client_in.model_dump(),
        company_id=current_user.company_id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client

@router.get("/{client_id}", response_model=schemas.Client)
async def read_client(
    *,
    db: AsyncSession = Depends(get_db),
    client_id: UUID,
    current_user: User = Depends(PermissionChecker("manage_clients")),
) -> Any:
    """
    Get client by ID.
    """
    query = select(Client).where(
        Client.id == client_id, 
        Client.company_id == current_user.company_id
    )
    result = await db.execute(query)
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    return client

@router.put("/{client_id}", response_model=schemas.Client)
async def update_client(
    *,
    db: AsyncSession = Depends(get_db),
    client_id: UUID,
    client_in: schemas.ClientUpdate,
    current_user: User = Depends(PermissionChecker("manage_clients")),
) -> Any:
    """
    Update a client.
    """
    query = select(Client).where(
        Client.id == client_id,
        Client.company_id == current_user.company_id
    )
    result = await db.execute(query)
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    update_data = client_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)
        
    client.updated_by_id = current_user.id
        
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client

@router.delete("/{client_id}", response_model=schemas.Client)
async def delete_client(
    *,
    db: AsyncSession = Depends(get_db),
    client_id: UUID,
    current_user: User = Depends(PermissionChecker("manage_clients")),
) -> Any:
    """
    Delete a client.
    """
    query = select(Client).where(
        Client.id == client_id,
        Client.company_id == current_user.company_id
    )
    result = await db.execute(query)
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    await db.delete(client)
    await db.commit()
    return client


# ──────────── CRM / Credit Features ────────────

@router.get("/{client_id}/statement", response_model=account_ledger_schemas.StatementResponse)
async def get_client_statement(
    *,
    db: AsyncSession = Depends(get_db),
    client_id: UUID,
    current_user: User = Depends(PermissionChecker("manage_clients")),
) -> Any:
    """Get the financial statement and ledger entries for a client."""
    from app.models.account_ledger import AccountLedger, PartnerType
    from sqlalchemy import desc

    # Verify client exists
    query = select(Client).where(Client.id == client_id, Client.company_id == current_user.company_id)
    result = await db.execute(query)
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    ledger_query = select(AccountLedger).where(
        AccountLedger.partner_id == client_id,
        AccountLedger.partner_type == PartnerType.CLIENT
    ).order_by(desc(AccountLedger.created_at))
    ledger_result = await db.execute(ledger_query)
    entries = ledger_result.scalars().all()

    return {
        "current_balance": client.current_balance,
        "credit_limit": client.credit_limit,
        "entries": entries
    }

@router.post("/{client_id}/payments", response_model=account_ledger_schemas.LedgerEntry)
async def register_client_payment(
    *,
    db: AsyncSession = Depends(get_db),
    client_id: UUID,
    payment_in: account_ledger_schemas.PaymentRequest,
    current_user: User = Depends(PermissionChecker("manage_clients")),
) -> Any:
    """Register a payment to lower a client's debt balance."""
    from app.models.account_ledger import AccountLedger, LedgerType, PartnerType

    if payment_in.amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than 0")

    query = select(Client).where(Client.id == client_id, Client.company_id == current_user.company_id)
    result = await db.execute(query)
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Lower the current balance (debt)
    new_balance = client.current_balance - payment_in.amount
    client.current_balance = new_balance

    # Record ledger entry
    ledger_entry = AccountLedger(
        partner_id=client.id,
        partner_type=PartnerType.CLIENT,
        type=LedgerType.PAYMENT,
        amount=payment_in.amount,
        balance_after=new_balance,
        reference_id=payment_in.reference_id,
        description=payment_in.description,
    )
    db.add(ledger_entry)
    await db.commit()
    await db.refresh(ledger_entry)

    return ledger_entry


@router.get("/{client_id}/activities", response_model=List[schemas.Activity])
async def get_client_activities(
    *,
    db: AsyncSession = Depends(get_db),
    client_id: UUID,
    current_user: User = Depends(PermissionChecker("manage_clients")),
) -> Any:
    """Get all activity logs for a client."""
    query = select(ClientActivity).where(
        ClientActivity.client_id == client_id,
        ClientActivity.company_id == current_user.company_id
    ).order_by(desc(ClientActivity.created_at))
    
    result = await db.execute(query)
    activities = result.scalars().all()
    
    # Enrich with user name (could be optimized with a join)
    enriched = []
    for a in activities:
        user_query = select(User).where(User.id == a.user_id)
        u_res = await db.execute(user_query)
        u = u_res.scalar_one_or_none()
        
        act_dict = {
            "id": a.id,
            "client_id": a.client_id,
            "user_id": a.user_id,
            "type": a.type,
            "content": a.content,
            "created_at": a.created_at,
            "user_name": u.full_name if u else "Desconocido"
        }
        enriched.append(act_dict)
        
    return enriched


@router.post("/{client_id}/activities", response_model=schemas.Activity)
async def create_client_activity(
    *,
    db: AsyncSession = Depends(get_db),
    client_id: UUID,
    activity_in: schemas.ActivityCreate,
    current_user: User = Depends(PermissionChecker("manage_clients")),
) -> Any:
    """Create a new activity log (note, call, etc) for a client."""
    activity = ClientActivity(
        **activity_in.model_dump(),
        client_id=client_id,
        user_id=current_user.id,
        company_id=current_user.company_id
    )
    db.add(activity)
    
    # Update last interaction
    client_query = select(Client).where(Client.id == client_id)
    c_res = await db.execute(client_query)
    client = c_res.scalar_one_or_none()
    if client:
        client.last_interaction_at = func.now()
        db.add(client)
        
    await db.commit()
    await db.refresh(activity)
    
    return {
        **activity.__dict__,
        "user_name": current_user.full_name
    }


@router.get("/{client_id}/stats", response_model=schemas.ClientStats)
async def get_client_stats(
    *,
    db: AsyncSession = Depends(get_db),
    client_id: UUID,
    current_user: User = Depends(PermissionChecker("manage_clients")),
) -> Any:
    """Get CRM statistics for a client (LTV, AOV, etc)."""
    # Total sales and count
    sales_query = select(
        func.sum(Sale.total).label("total_sales"),
        func.count(Sale.id).label("order_count"),
        func.max(Sale.created_at).label("last_sale_at")
    ).where(
        Sale.client_id == client_id,
        Sale.company_id == current_user.company_id,
        Sale.is_active == True
    )
    
    result = await db.execute(sales_query)
    stats = result.one()
    
    total_sales = float(stats.total_sales or 0)
    order_count = int(stats.order_count or 0)
    avg_value = total_sales / order_count if order_count > 0 else 0
    
    return {
        "total_sales": total_sales,
        "order_count": order_count,
        "average_order_value": avg_value,
        "last_sale_at": stats.last_sale_at
    }


@router.get("/{client_id}/timeline", response_model=List[schemas.UnifiedTimelineItem])
async def get_client_timeline(
    *,
    db: AsyncSession = Depends(get_db),
    client_id: UUID,
    current_user: User = Depends(PermissionChecker("manage_clients")),
) -> Any:
    """Get a unified timeline of activities and ledger movements."""
    timeline = []
    
    # 1. Activities
    act_query = select(ClientActivity).where(ClientActivity.client_id == client_id).order_by(desc(ClientActivity.created_at)).limit(50)
    act_res = await db.execute(act_query)
    for a in act_res.scalars().all():
        timeline.append({
            "id": a.id,
            "type": "ACTIVITY",
            "category": a.type,
            "content": a.content,
            "created_at": a.created_at
        })
        
    # 2. Ledger Entries
    led_query = select(AccountLedger).where(
        AccountLedger.partner_id == client_id,
        AccountLedger.partner_type == PartnerType.CLIENT
    ).order_by(desc(AccountLedger.created_at)).limit(50)
    led_res = await db.execute(led_query)
    for l in led_res.scalars().all():
        timeline.append({
            "id": l.id,
            "type": "LEDGER",
            "category": l.type,
            "content": l.description or f"Movimiento de {l.type}",
            "amount": float(l.amount),
            "created_at": l.created_at
        })
        
    # Sort unified timeline
    timeline.sort(key=lambda x: x["created_at"], reverse=True)
    return timeline[:50]


@router.get("/{client_id}/sales", response_model=ClientSalesResponse)
async def get_client_sales(
    *,
    db: AsyncSession = Depends(get_db),
    client_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1),
    current_user: User = Depends(PermissionChecker("manage_clients")),
) -> Any:
    """Get sales history for a specific client."""
    query = select(Sale).where(
        Sale.client_id == client_id,
        Sale.company_id == current_user.company_id
    ).options(
        selectinload(Sale.branch),
        selectinload(Sale.client),
        selectinload(Sale.user)
    ).order_by(desc(Sale.created_at))
    
    # Total count for pagination
    count_query = select(func.count()).select_from(query.subquery())
    count_res = await db.execute(count_query)
    total = count_res.scalar_one()
    
    # Execution
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    sales = result.scalars().all()
    
    return {
        "total": total,
        "items": sales
    }



