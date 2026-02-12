from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.plan import Plan
from app.models.user import User
from app.schemas import plan as schemas
from app.core.permissions import PermissionChecker
import uuid

router = APIRouter()

@router.get("/", response_model=List[schemas.Plan])
async def read_plans(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve plans. Public endpoint (for pricing page).
    """
    query = select(Plan).where(Plan.is_active == True).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/all", response_model=List[schemas.Plan])
async def read_all_plans(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(PermissionChecker("manage_saas")),
) -> Any:
    """
    Retrieve all plans (including inactive). Super Admin only.
    """
    query = select(Plan).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=schemas.Plan)
async def create_plan(
    *,
    db: AsyncSession = Depends(get_db),
    plan_in: schemas.PlanCreate,
    current_user: User = Depends(PermissionChecker("manage_saas")),
) -> Any:
    """
    Create new plan.
    """
    plan = Plan(**plan_in.model_dump())
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan

@router.put("/{id}", response_model=schemas.Plan)
async def update_plan(
    *,
    db: AsyncSession = Depends(get_db),
    id: uuid.UUID,
    plan_in: schemas.PlanUpdate,
    current_user: User = Depends(PermissionChecker("manage_saas")),
) -> Any:
    """
    Update a plan.
    """
    result = await db.execute(select(Plan).where(Plan.id == id))
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    update_data = plan_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)
        
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan
