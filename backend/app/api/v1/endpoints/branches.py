from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.core.database import get_db
from app.models.branch import Branch
from app.models.user import User
from app.schemas import branch as schemas
from app.core.permissions import PermissionChecker
from app.core.plan_limits import PlanLimitChecker

router = APIRouter()

@router.get("/", response_model=List[schemas.Branch])
async def read_branches(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve branches.
    """
    if current_user.is_superuser:
         # Superuser sees all? Or should select company? 
         # For now, let's assume superuser sees all or we don't expose this yet for superuser global view here.
         # Actually, better to stick to current_user.company_id for now.
         pass
    
    query = select(Branch).where(Branch.company_id == current_user.company_id).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=schemas.Branch)
async def create_branch(
    *,
    db: AsyncSession = Depends(get_db),
    branch_in: schemas.BranchCreate,
    current_user: User = Depends(PermissionChecker("manage_settings")), 
    _plan: User = Depends(PlanLimitChecker(resource="branches", count_model=Branch)),
) -> Any:
    """
    Create new branch.
    """
    branch = Branch(
        **branch_in.dict(),
        company_id=current_user.company_id
    )
    db.add(branch)
    await db.commit()
    await db.refresh(branch)
    return branch

@router.put("/{id}", response_model=schemas.Branch)
async def update_branch(
    *,
    db: AsyncSession = Depends(get_db),
    id: str,
    branch_in: schemas.BranchUpdate,
    current_user: User = Depends(PermissionChecker("manage_settings")),
) -> Any:
    """
    Update a branch.
    """
    branch = await db.get(Branch, id)
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    if branch.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    update_data = branch_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(branch, field, value)
        
    db.add(branch)
    await db.commit()
    await db.refresh(branch)
    return branch

@router.delete("/{id}", response_model=schemas.Branch)
async def delete_branch(
    *,
    db: AsyncSession = Depends(get_db),
    id: str,
    current_user: User = Depends(PermissionChecker("manage_settings")),
) -> Any:
    """
    Delete a branch.
    """
    branch = await db.get(Branch, id)
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    if branch.company_id != current_user.company_id:
         raise HTTPException(status_code=403, detail="Not enough permissions")

    await db.delete(branch)
    await db.commit()
    return branch
