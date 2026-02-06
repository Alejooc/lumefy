from typing import Any, List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import schemas
from app.core import auth
from app.core.database import get_db
from app.models.category import Category
from app.models.user import User

router = APIRouter()

@router.get("/", response_model=List[schemas.Category])
async def read_categories(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Retrieve categories.
    """
    query = select(Category).where(
        Category.company_id == current_user.company_id,
        Category.is_active == True
    ).offset(skip).limit(limit)
    result = await db.execute(query)
    categories = result.scalars().all()
    return categories

@router.post("/", response_model=schemas.Category)
async def create_category(
    *,
    db: AsyncSession = Depends(get_db),
    category_in: schemas.CategoryCreate,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Create new category.
    """
    try:
        category = Category(**category_in.model_dump(), company_id=current_user.company_id)
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{category_id}", response_model=schemas.Category)
async def update_category(
    *,
    db: AsyncSession = Depends(get_db),
    category_id: uuid.UUID,
    category_in: schemas.CategoryUpdate,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Update a category.
    """
    result = await db.execute(select(Category).where(
        Category.id == category_id,
        Category.company_id == current_user.company_id
    ))
    category = result.scalars().first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
        
    update_data = category_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
        
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category

@router.get("/{category_id}", response_model=schemas.Category)
async def read_category(
    *,
    db: AsyncSession = Depends(get_db),
    category_id: uuid.UUID,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Get category by ID.
    """
    result = await db.execute(select(Category).where(
        Category.id == category_id,
        Category.company_id == current_user.company_id
    ))
    category = result.scalars().first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

@router.delete("/{category_id}", response_model=schemas.Category)
async def delete_category(
    *,
    db: AsyncSession = Depends(get_db),
    category_id: uuid.UUID,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Delete a category (soft delete).
    """
    result = await db.execute(select(Category).where(
        Category.id == category_id,
        Category.company_id == current_user.company_id
    ))
    category = result.scalars().first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
        
    category.is_active = False # Soft delete
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category
