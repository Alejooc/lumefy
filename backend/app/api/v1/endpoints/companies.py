from typing import Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core import auth
from app.models.user import User
from app.models.company import Company
from app.schemas import company as schemas

router = APIRouter()

@router.get("/me", response_model=schemas.Company)
async def read_current_company(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Get current user's company details.
    """
    if not current_user.company_id:
        raise HTTPException(status_code=404, detail="User does not belong to any company")
        
    result = await db.execute(select(Company).where(Company.id == current_user.company_id))
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
        
    return company

@router.put("/me", response_model=schemas.Company)
async def update_current_company(
    company_in: schemas.CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Update current user's company details.
    """
    if not current_user.company_id:
        raise HTTPException(status_code=404, detail="User does not belong to any company")
        
    result = await db.execute(select(Company).where(Company.id == current_user.company_id))
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
        
    # Update fields
    update_data = company_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(company, field, value)
        
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company
