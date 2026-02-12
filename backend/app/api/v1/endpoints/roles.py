from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import auth
from app.core.permissions import PermissionChecker
from app.core.database import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas import role as schemas
from app.core.audit import log_activity

router = APIRouter()

@router.get("/", response_model=List[schemas.Role])
async def read_roles(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(PermissionChecker("manage_users")),
) -> Any:
    """
    Retrieve all roles for current company.
    """
    query = select(Role).where(
        Role.company_id == current_user.company_id
    ).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{role_id}", response_model=schemas.Role)
async def read_role(
    *,
    db: AsyncSession = Depends(get_db),
    role_id: UUID,
    current_user: User = Depends(PermissionChecker("manage_users")),
) -> Any:
    """
    Get role by ID.
    """
    result = await db.execute(select(Role).where(
        Role.id == role_id,
        Role.company_id == current_user.company_id
    ))
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
        
    return role

@router.post("/", response_model=schemas.Role)
async def create_role(
    *,
    db: AsyncSession = Depends(get_db),
    role_in: schemas.RoleCreate,
    current_user: User = Depends(PermissionChecker("manage_users")),
) -> Any:
    """
    Create a new role.
    """
    role = Role(
        **role_in.model_dump(),
        company_id=current_user.company_id
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    await log_activity(db, "CREATE", "Role", role.id, current_user.id, current_user.company_id)
    return role

@router.put("/{role_id}", response_model=schemas.Role)
async def update_role(
    *,
    db: AsyncSession = Depends(get_db),
    role_id: UUID,
    role_in: schemas.RoleUpdate,
    current_user: User = Depends(PermissionChecker("manage_users")),
) -> Any:
    """
    Update a role.
    """
    result = await db.execute(select(Role).where(
        Role.id == role_id,
        Role.company_id == current_user.company_id
    ))
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    update_data = role_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(role, field, value)
    
    db.add(role)
    await db.commit()
    await db.refresh(role)
    await log_activity(db, "UPDATE", "Role", role.id, current_user.id, current_user.company_id)
    return role

@router.delete("/{role_id}", response_model=schemas.Role)
async def delete_role(
    *,
    db: AsyncSession = Depends(get_db),
    role_id: UUID,
    current_user: User = Depends(PermissionChecker("manage_users")),
) -> Any:
    """
    Delete a role. Fails if users are still assigned to it.
    """
    result = await db.execute(select(Role).where(
        Role.id == role_id,
        Role.company_id == current_user.company_id
    ))
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Check if users are assigned to this role
    users_result = await db.execute(
        select(User).where(User.role_id == role_id).limit(1)
    )
    if users_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400, 
            detail="No se puede eliminar el rol porque tiene usuarios asignados"
        )
    
    await db.delete(role)
    await db.commit()
    await log_activity(db, "DELETE", "Role", role_id, current_user.id, current_user.company_id)
    return role
