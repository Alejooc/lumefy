from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import auth
from app.core.database import get_db
from app.core.security import get_password_hash
from app.core.security import get_password_hash
from app.models.user import User
from app.core.permissions import PermissionChecker # Added Import
from app.schemas import user as schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.User])
async def read_users(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Retrieve users.
    """
    query = select(User).where(User.company_id == current_user.company_id).offset(skip).limit(limit)
    result = await db.execute(query)
    # unique() is recommended with joinedload even for M2O to be safe/consistent
    return result.scalars().unique().all()

@router.get("/{user_id}", response_model=schemas.User)
async def read_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_id: UUID,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Get user by ID.
    """
    query = select(User).where(
        User.id == user_id, 
        User.company_id == current_user.company_id
    )
    
    result = await db.execute(query)
    user = result.scalars().first() # Use scalar/first
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return user

@router.post("/", response_model=schemas.User)
async def create_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: schemas.UserCreate,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Create new user.
    """
    # Check if user with email already exists
    print(f"DEBUG: Creating user with email {user_in.email} and role {user_in.role_id}")
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=400, detail="The user with this email already exists in the system.")
    
    try:
        user_data = user_in.model_dump(exclude={"password"})
        user_data["hashed_password"] = get_password_hash(user_in.password)
        user_data["company_id"] = current_user.company_id # Force company association
        
        user = User(**user_data)
        user.created_by_id = current_user.id
        user.updated_by_id = current_user.id
        
        db.add(user)
        await db.commit()
        
        # Fetch with role for response
        query = select(User).where(User.id == user.id)
        result = await db.execute(query)
        user = result.scalars().first()
        
        return user
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{user_id}", response_model=schemas.User)
async def update_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_id: UUID,
    user_in: schemas.UserUpdate,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Update a user.
    """
    query = select(User).where(
        User.id == user_id, 
        User.company_id == current_user.company_id
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    try:
        update_data = user_in.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
            
        for field, value in update_data.items():
            setattr(user, field, value)
            
        user.updated_by_id = current_user.id
            
        db.add(user)
        await db.commit()
        
        # Fetch with role for response
        query = select(User).where(User.id == user.id)
        result = await db.execute(query)
        user = result.scalars().first()
        
        return user
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{user_id}", response_model=schemas.User)
async def delete_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_id: UUID,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Delete a user.
    """
    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Users cannot delete themselves")

    query = select(User).where(
        User.id == user_id,
        User.company_id == current_user.company_id
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    await db.delete(user)
    await db.commit()
    return user
