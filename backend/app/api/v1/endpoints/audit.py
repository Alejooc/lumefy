from typing import Any, List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import auth
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.core.permissions import PermissionChecker
from app.schemas import audit as schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.AuditLog])
async def read_audit_logs(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[UUID] = None,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(PermissionChecker("view_reports"))
) -> Any:
    """
    Retrieve audit logs with optional filters.
    """
    if current_user.is_superuser:
        query = select(AuditLog)
    else:
        query = select(AuditLog).where(AuditLog.company_id == current_user.company_id)
    
    # Eager load user
    query = query.options(joinedload(AuditLog.user))
    
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if date_from:
        try:
            parsed = datetime.fromisoformat(date_from)
            query = query.where(AuditLog.created_at >= parsed)
        except ValueError:
            pass
    if date_to:
        try:
            parsed = datetime.fromisoformat(date_to)
            # Include the full end day
            if parsed.hour == 0 and parsed.minute == 0:
                parsed = parsed + timedelta(days=1) - timedelta(seconds=1)
            query = query.where(AuditLog.created_at <= parsed)
        except ValueError:
            pass
        
    query = query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return logs

