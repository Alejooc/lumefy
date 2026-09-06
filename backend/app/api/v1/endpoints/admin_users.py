from typing import Any, List
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, select
from app.core import auth, security
from app.core.database import get_db
from app.models.user import User
from app.models.role import Role
from app.schemas import user as schemas
from app.core.config import settings
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID, uuid4
from app.core.audit import get_impersonation_context, log_activity

router = APIRouter()


async def _create_impersonation_response(
    db: AsyncSession,
    *,
    operator: User,
    target: User,
    reason: str,
) -> dict[str, Any]:
    reason = reason.strip()
    if len(reason) < 3:
        raise HTTPException(status_code=422, detail="Indica un motivo de soporte de al menos 3 caracteres")

    session_id = uuid4()
    started_at = datetime.now(timezone.utc).isoformat()
    access_token = auth.create_access_token(
        data={
            "sub": target.email,
            "scope": "impersonation",
            "impersonated_by_user_id": str(operator.id),
            "impersonation_session_id": str(session_id),
            "impersonation_started_at": started_at,
            "impersonation_reason": reason,
            "auth_version": getattr(target, "auth_token_version", 0) or 0,
        },
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    await log_activity(
        db,
        action="IMPERSONATION_START",
        entity_type="ImpersonationSession",
        entity_id=session_id,
        user_id=operator.id,
        company_id=target.company_id,
        details={
            "operator_user_id": str(operator.id),
            "target_user_id": str(target.id),
            "target_company_id": str(target.company_id) if target.company_id else None,
            "reason": reason,
            "started_at": started_at,
        },
    )
    await db.commit()
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "session_id": str(session_id),
        "started_at": started_at,
        "user": schemas.User.model_validate(target),
    }

@router.get("", response_model=List[schemas.User])
async def read_users(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Retrieve all users (Super Admin only).
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    query = select(User).where(or_(User.role_id.is_not(None), User.is_superuser == True))
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (User.email.ilike(search_term)) | 
            (User.full_name.ilike(search_term))
        )
    
    result = await db.execute(query.offset(skip).limit(limit))
    users = result.scalars().all()
    return [schemas.User.model_validate(u) for u in users]

@router.post("/{user_id}/impersonate", response_model=Any)
async def impersonate_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_id: UUID,
    payload: schemas.ImpersonationRequest = Body(...),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Impersonate another user (Super Admin only).
    Returns an access token for the target user.
    """
    # Verify Super Admin
    if not current_user.is_superuser:
         raise HTTPException(status_code=403, detail="Not enough permissions")

    # Get Target User
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.is_active == True,
            or_(User.role_id.is_not(None), User.is_superuser == True),
        )
    )
    target_user = result.scalars().first()
    
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return await _create_impersonation_response(
        db,
        operator=current_user,
        target=target_user,
        reason=payload.reason,
    )


@router.post("/impersonation/end", response_model=Any)
async def end_impersonation(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """Record the end of a support session before the client restores its token."""

    context = get_impersonation_context()
    if not context:
        raise HTTPException(status_code=409, detail="No hay una sesión de soporte delegada activa")

    ended_at = datetime.now(timezone.utc).isoformat()
    await log_activity(
        db,
        action="IMPERSONATION_END",
        entity_type="ImpersonationSession",
        entity_id=context["session_id"],
        user_id=current_user.id,
        company_id=current_user.company_id,
        details={
            "operator_user_id": context["operator_user_id"],
            "target_user_id": str(current_user.id),
            "target_company_id": str(current_user.company_id) if current_user.company_id else None,
            "reason": context["reason"],
            "started_at": context["started_at"],
            "ended_at": ended_at,
        },
    )
    await db.commit()
    return {"ok": True, "session_id": context["session_id"], "ended_at": ended_at}

@router.post("/impersonate-company/{company_id}", response_model=Any)
async def impersonate_company(
    *,
    db: AsyncSession = Depends(get_db),
    company_id: UUID,
    payload: schemas.ImpersonationRequest = Body(...),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Impersonate the admin of a company (Super Admin only).
    """
    # Verify Super Admin
    if not current_user.is_superuser:
         raise HTTPException(status_code=403, detail="Not enough permissions")

    # Only impersonate an actual tenant administrator. The former case-sensitive
    # match fell back to the first company user, which could be a limited role.
    query = select(User).join(User.role).where(
        User.company_id == company_id,
        User.is_active == True,
        func.upper(Role.name).in_(["ADMINISTRADOR", "ADMIN", "ADMINISTRATOR"]),
    ).order_by(User.created_at.asc())
    result = await db.execute(query)
    target_user = result.scalars().first()

    if not target_user:
        raise HTTPException(
            status_code=409,
            detail="La empresa no tiene un administrador activo para impersonar",
        )
        
    return await _create_impersonation_response(
        db,
        operator=current_user,
        target=target_user,
        reason=payload.reason,
    )
