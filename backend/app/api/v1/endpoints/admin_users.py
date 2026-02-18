from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core import auth, security
from app.core.database import get_db
from app.models.user import User
from app.schemas import user as schemas
from app.core.config import settings
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

router = APIRouter()

@router.get("", response_model=List[schemas.User])
async def read_users(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Retrieve all users (Super Admin only).
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    query = select(User)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (User.email.ilike(search_term)) | 
            (User.full_name.ilike(search_term))
        )
    
    result = await db.execute(query.offset(skip).limit(limit))
    users = result.scalars().all()
    return [schemas.User.model_validate(u) for u in users]

@router.post("/{user_id}/impersonate", response_model=Any)
async def impersonate_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_id: UUID,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Impersonate another user (Super Admin only).
    Returns an access token for the target user.
    """
    # Verify Super Admin
    if not current_user.is_superuser:
         raise HTTPException(status_code=403, detail="Not enough permissions")

    # Get Target User
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalars().first()
    
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Generate Token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": target_user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": schemas.User.model_validate(target_user)
    }

@router.post("/impersonate-company/{company_id}", response_model=Any)
async def impersonate_company(
    *,
    db: AsyncSession = Depends(get_db),
    company_id: UUID,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Impersonate the admin of a company (Super Admin only).
    """
    # Verify Super Admin
    if not current_user.is_superuser:
         raise HTTPException(status_code=403, detail="Not enough permissions")

    # Find Admin User for Company
    # Strategy: Find user with "Administrador" role in this company, or fallback to first user
    query = select(User).join(User.role).where(
        User.company_id == company_id,
        User.role.has(name="Administrador")
    )
    result = await db.execute(query)
    target_user = result.scalars().first()
    
    # Fallback to any user if no specific "Administrador" found (e.g. customized roles)
    if not target_user:
        result = await db.execute(select(User).where(User.company_id == company_id).limit(1))
        target_user = result.scalars().first()
        
    if not target_user:
        raise HTTPException(status_code=404, detail="No users found for this company")
        
    # Generate Token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": target_user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": schemas.User.model_validate(target_user)
    }
