from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import auth
from app.core.database import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas import role as schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.Role])
async def read_roles(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Retrieve all roles.
    """
    query = select(Role).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{role_id}", response_model=schemas.Role)
async def read_role(
    *,
    db: AsyncSession = Depends(get_db),
    role_id: UUID,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Get role by ID.
    """
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
        
    return role
