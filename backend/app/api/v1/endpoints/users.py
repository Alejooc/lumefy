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
from app.core.permissions import PermissionChecker 
from app.core.audit import log_activity
from app.schemas import user as schemas

router = APIRouter()

@router.get("/me", response_model=schemas.User)
async def read_user_me(
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Get current user.
    """
    print(f"DEBUG: /me called. User: {current_user.email}, Role: {current_user.role}")
    return current_user

@router.get("/", response_model=List[schemas.User])
async def read_users(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(PermissionChecker("manage_users")),
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
    current_user: User = Depends(PermissionChecker("manage_users")),
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
    current_user: User = Depends(PermissionChecker("manage_users")),
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
        
        # Log Activity
        await log_activity(
            db,
            action="CREATE",
            entity_type="User",
            entity_id=user.id,
            user_id=current_user.id,
            company_id=current_user.company_id,
            details={"email": user.email, "role": user.role_id}
        )

        # --- Welcome Notification ---
        from app.models.notification import Notification
        from app.models.notification_template import NotificationTemplate
        from app.schemas.notification import NotificationType
        
        # 1. Get Template
        template_result = await db.execute(select(NotificationTemplate).where(NotificationTemplate.code == 'WELCOME'))
        template = template_result.scalars().first()
        
        if template and template.is_active:
             # 3. Format Message
            title = template.title_template
            message = template.body_template.format(
                user_name=user.full_name or 'Usuario'
            )
            
            notification = Notification(
                user_id=user.id,
                type=template.type,
                title=title,
                message=message,
                link="/dashboard"
            )
            db.add(notification)
            await db.commit()
        # ----------------------------

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
    # Allow user to update themselves, otherwise check for permission
    if current_user.id != user_id:
        permission_checker = PermissionChecker("manage_users")
        permission_checker(current_user)

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
        
        # Log Activity
        await log_activity(
            db,
            action="UPDATE",
            entity_type="User",
            entity_id=user.id,
            user_id=current_user.id,
            company_id=current_user.company_id,
            details=update_data
        )

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
    current_user: User = Depends(PermissionChecker("manage_users")),
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
    
    # Log Activity
    await log_activity(
        db,
        action="DELETE",
        entity_type="User",
        entity_id=user_id,
        user_id=current_user.id,
        company_id=current_user.company_id
    )
    
    return user

@router.post("/{user_id}/recovery-email", response_model=Any)
async def send_recovery_email(
    *,
    db: AsyncSession = Depends(get_db),
    user_id: UUID,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Send password recovery email to a specific user (Admin only).
    """
    # Check permissions (Super Admin or Company Admin)
    permission_checker = PermissionChecker("manage_users")
    permission_checker(current_user)
    
    query = select(User).where(User.id == user_id)
    if not current_user.is_superuser:
        query = query.where(User.company_id == current_user.company_id)
        
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Generate Reset Token
    from app.services.email import EmailService
    from datetime import timedelta
    from app.core import auth
    from app.core.config import settings

    access_token_expires = timedelta(hours=1)
    reset_token = auth.create_access_token(
        data={"sub": user.email, "type": "reset"},
        expires_delta=access_token_expires
    )
    
    try:
        await EmailService.send_reset_password_email(user.email, reset_token)
    except Exception as e:
        # Log error but don't crash if SMTP is not configured
        print(f"ERROR: Failed to send email: {e}")
        # In DEV without SMTP, print the link
        print(f"DEBUG LINK: http://localhost:4200/reset-password?token={reset_token}")
        if settings.ENVIRONMENT == "production":
             raise HTTPException(status_code=500, detail="Failed to send email")
    
    # Log Activity
    await log_activity(
        db,
        action="UPDATE",
        entity_type="User",
        entity_id=user.id,
        user_id=current_user.id,
        company_id=current_user.company_id,
        details={"action": "password_recovery_email"}
    )
    
    return {"message": "Recovery email sent successfully"}
