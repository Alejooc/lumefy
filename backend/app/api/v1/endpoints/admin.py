from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.company import Company
from app.models.user import User
from app.schemas import company as schemas
from app.core.permissions import PermissionChecker
import uuid

# This router should be protected. 
# For now we use a permission 'manage_saas' which superusers should have by default.
# Or we can check current_user.is_superuser

router = APIRouter()

@router.get("/companies", response_model=List[schemas.Company])
async def read_companies(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(PermissionChecker("manage_saas")), # Need to ensure this permission exists or use is_superuser check
) -> Any:
    """
    Retrieve all companies (Super Admin only).
    """
    query = select(Company).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/companies", response_model=schemas.Company)
async def create_company(
    *,
    db: AsyncSession = Depends(get_db),
    company_in: schemas.CompanyCreate,
    current_user: User = Depends(PermissionChecker("manage_saas")),
) -> Any:
    """
    Register a new company (Tenant).
    """
    # Check if company with same name exists? 
    # For now strict check might annoying, but let's assume unique names for simplicity if we enforced it (we didn't in model but index=True)
    
    company = Company(
        name=company_in.name,
        tax_id=company_in.tax_id,
        address=company_in.address,
        email=company_in.email,
        phone=company_in.phone,
        plan=company_in.plan or "FREE",
        valid_until=company_in.valid_until,
        is_active=True
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company

@router.put("/companies/{id}", response_model=schemas.Company)
async def update_company(
    *,
    db: AsyncSession = Depends(get_db),
    id: uuid.UUID,
    company_in: schemas.CompanyUpdate,
    current_user: User = Depends(PermissionChecker("manage_saas")),
) -> Any:
    """
    Update company details (including plan/status).
    """
    result = await db.execute(select(Company).where(Company.id == id))
    company = result.scalars().first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
        
    update_data = company_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(company, field, value)
        
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company
