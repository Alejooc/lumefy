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
