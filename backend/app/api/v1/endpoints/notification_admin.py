from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.core.database import get_db
from app.core import auth
from app.models.user import User
from app.models.notification import Notification
from app.models.notification_template import NotificationTemplate
from app.schemas import notification_template as schemas
from app.schemas.notification import NotificationType

router = APIRouter()

@router.get("/templates", response_model=List[schemas.NotificationTemplate])
async def read_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    List all notification templates (Super Admin).
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    result = await db.execute(select(NotificationTemplate))
    return result.scalars().all()

@router.post("/templates", response_model=schemas.NotificationTemplate)
async def create_template(
    *,
    db: AsyncSession = Depends(get_db),
    template_in: schemas.NotificationTemplateCreate,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Create a new notification template (Super Admin).
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    # Check if code exists
    result = await db.execute(select(NotificationTemplate).where(NotificationTemplate.code == template_in.code))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Template with this code already exists")
        
    template = NotificationTemplate(**template_in.model_dump())
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template

@router.put("/templates/{id}", response_model=schemas.NotificationTemplate)
async def update_template(
    *,
    db: AsyncSession = Depends(get_db),
    id: UUID,
    template_in: schemas.NotificationTemplateUpdate,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Update a notification template.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    result = await db.execute(select(NotificationTemplate).where(NotificationTemplate.id == id))
    template = result.scalars().first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
        
    update_data = template_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
        
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template

@router.post("/send", response_model=dict)
async def send_manual_notification(
    *,
    db: AsyncSession = Depends(get_db),
    notification_in: schemas.ManualNotification,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Send a manual notification to one or all users.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    target_users = []
    
    if notification_in.target_all:
        # Broadcast to all users in the system
        result = await db.execute(select(User))
        target_users = result.scalars().all()
    elif notification_in.user_id:
        result = await db.execute(select(User).where(User.id == notification_in.user_id))
        user = result.scalars().first()
        if user:
            target_users = [user]
    else:
        raise HTTPException(status_code=400, detail="Must specify user_id or target_all=True")
        
    count = 0
    for user in target_users:
        if not user.id: continue # Should not happen
        
        notif = Notification(
            user_id=user.id,
            type=notification_in.type,
            title=notification_in.title,
            message=notification_in.message,
            link=notification_in.link
        )
        db.add(notif)
        count += 1
        
    await db.commit()
    
    return {"message": f"Notification sent to {count} users"}
