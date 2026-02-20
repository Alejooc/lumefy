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
from app.schemas import client as schemas
from app.schemas import account_ledger as account_ledger_schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.Client])
async def read_clients(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    q: str = Query(None, min_length=1),
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

