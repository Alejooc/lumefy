from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import auth
from app.core.database import get_db
from app.models.supplier import Supplier
from app.models.user import User
from app.core.permissions import PermissionChecker
from app.core.audit import log_activity
from app.schemas import supplier as schemas
from app.schemas import account_ledger as account_ledger_schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.Supplier])
async def read_suppliers(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(PermissionChecker("view_products")), # Using view_products for now
) -> Any:
    """
    Retrieve suppliers.
    """
    query = select(Supplier).where(Supplier.company_id == current_user.company_id).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=schemas.Supplier)
async def create_supplier(
    *,
    db: AsyncSession = Depends(get_db),
    supplier_in: schemas.SupplierCreate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """
    Create new supplier.
    """
    supplier = Supplier(**supplier_in.model_dump(), company_id=current_user.company_id)
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    
    await log_activity(db, "CREATE", "Supplier", supplier.id, current_user.id, current_user.company_id, supplier_in.model_dump())
    
    return supplier

@router.put("/{supplier_id}", response_model=schemas.Supplier)
async def update_supplier(
    *,
    db: AsyncSession = Depends(get_db),
    supplier_id: UUID,
    supplier_in: schemas.SupplierUpdate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """
    Update a supplier.
    """
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id, Supplier.company_id == current_user.company_id))
    supplier = result.scalars().first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
        
    update_data = supplier_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplier, field, value)
        
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    
    await log_activity(db, "UPDATE", "Supplier", supplier.id, current_user.id, current_user.company_id, update_data)
    
    return supplier

@router.delete("/{supplier_id}", response_model=schemas.Supplier)
async def delete_supplier(
    *,
    db: AsyncSession = Depends(get_db),
    supplier_id: UUID,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """
    Delete a supplier.
    """
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id, Supplier.company_id == current_user.company_id))
    supplier = result.scalars().first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
        
    await db.delete(supplier)
    await db.commit()
    
    await log_activity(db, "DELETE", "Supplier", supplier_id, current_user.id, current_user.company_id)
    
    return supplier


# ──────────── CRM / Credit Features ────────────

@router.get("/{supplier_id}/statement", response_model=account_ledger_schemas.StatementResponse)
async def get_supplier_statement(
    *,
    db: AsyncSession = Depends(get_db),
    supplier_id: UUID,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """Get the financial statement and ledger entries for a supplier."""
    from app.models.account_ledger import AccountLedger, PartnerType
    from sqlalchemy import desc

    # Verify supplier exists
    query = select(Supplier).where(Supplier.id == supplier_id, Supplier.company_id == current_user.company_id)
    result = await db.execute(query)
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    ledger_query = select(AccountLedger).where(
        AccountLedger.partner_id == supplier_id,
        AccountLedger.partner_type == PartnerType.SUPPLIER
    ).order_by(desc(AccountLedger.created_at))
    ledger_result = await db.execute(ledger_query)
    entries = ledger_result.scalars().all()

    return {
        "current_balance": supplier.current_balance,
        "credit_limit": supplier.credit_limit,
        "entries": entries
    }

@router.post("/{supplier_id}/payments", response_model=account_ledger_schemas.LedgerEntry)
async def register_supplier_payment(
    *,
    db: AsyncSession = Depends(get_db),
    supplier_id: UUID,
    payment_in: account_ledger_schemas.PaymentRequest,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """Register a payment to lower the debt balance with a supplier."""
    from app.models.account_ledger import AccountLedger, LedgerType, PartnerType

    if payment_in.amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than 0")

    query = select(Supplier).where(Supplier.id == supplier_id, Supplier.company_id == current_user.company_id)
    result = await db.execute(query)
    supplier = result.scalar_one_or_none()
    
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Lower the current balance (debt we owe)
    new_balance = supplier.current_balance - payment_in.amount
    supplier.current_balance = new_balance

    # Record ledger entry
    ledger_entry = AccountLedger(
        partner_id=supplier.id,
        partner_type=PartnerType.SUPPLIER,
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

