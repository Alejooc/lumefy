from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
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
    current_user: User = Depends(PermissionChecker("view_reports")) # Reusing a permission for now or add view_audit_logs
) -> Any:
    """
    Retrieve audit logs.
    """
    query = select(AuditLog).where(AuditLog.company_id == current_user.company_id)
    
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
        
    query = query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return logs
