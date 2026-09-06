from datetime import timedelta, datetime, timezone
import hmac
import json
import logging
import secrets
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.core import mfa
from app.core.auth import get_current_user
from app.models.user import User
from app.models.plan import Plan
from app.core.auth import create_access_token
from app.schemas.token import Token
from app.schemas.mfa import (
    MFAChallengeRequest,
    MFAEnableResponse,
    MFACodeRequest,
    MFASetupResponse,
    MFAStatusResponse,
    MFAVerifyResponse,
)
from app.core.rate_limit import limiter
from app.core.audit import get_impersonation_context, log_activity

router = APIRouter()
logger = logging.getLogger(__name__)


class Msg(BaseModel):
    msg: str


def _token_for_user(user: User) -> str:
    return create_access_token(
        data={"sub": user.email, "auth_version": getattr(user, "auth_token_version", 0) or 0},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _recovery_codes(raw: str | None) -> list[str]:
    try:
        value = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _require_superuser(user: User) -> None:
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="MFA solo está disponible para la cuenta dueña")
    if get_impersonation_context():
        raise HTTPException(status_code=403, detail="No puedes gestionar MFA desde una sesión de soporte suplantada")

@router.post("/login/access-token", response_model=Token)
@limiter.limit("5/minute")
async def login_access_token(
    request: Request,
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    # Find user
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    if user.is_superuser and user.mfa_enabled:
        challenge_id = secrets.token_urlsafe(24)
        challenge_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        user.mfa_challenge_hash = mfa.hash_challenge_id(challenge_id)
        user.mfa_challenge_expires_at = challenge_expires_at
        await db.commit()
        challenge_token = create_access_token(
            data={
                "sub": user.email,
                "type": "mfa_challenge",
                "jti": challenge_id,
            },
            expires_delta=timedelta(minutes=5),
        )
        return {
            "access_token": None,
            "token_type": "bearer",
            "mfa_required": True,
            "mfa_challenge": challenge_token,
        }

    return {
        "access_token": _token_for_user(user),
        "token_type": "bearer",
    }


@router.post("/login/mfa/verify", response_model=MFAVerifyResponse)
@limiter.limit("5/minute")
async def verify_mfa_login(
    request: Request,
    body: MFAChallengeRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Complete a password login with a one-time TOTP or recovery code."""

    try:
        payload = jwt.decode(body.challenge_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "mfa_challenge":
            raise ValueError("wrong token type")
        email = str(payload.get("sub") or "")
        challenge_id = str(payload.get("jti") or "")
        if not email or not challenge_id:
            raise ValueError("missing challenge claims")
    except (PyJWTError, ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=400, detail="El desafío MFA no es válido o expiró")

    result = await db.execute(
        select(User)
        .where(User.email == email, User.is_active == True)
        .with_for_update()
    )
    user = result.scalars().first()
    now = datetime.now(timezone.utc)
    if (
        not user
        or not user.is_superuser
        or not user.mfa_enabled
        or not user.mfa_challenge_hash
        or not hmac.compare_digest(user.mfa_challenge_hash, mfa.hash_challenge_id(challenge_id))
        or not user.mfa_challenge_expires_at
        or (_utc(user.mfa_challenge_expires_at) or now) <= now
    ):
        raise HTTPException(status_code=400, detail="El desafío MFA no es válido o expiró")

    accepted_step = mfa.verify_totp(user.mfa_secret_encrypted or "", body.code)
    if accepted_step is not None:
        if user.mfa_last_used_step is not None and accepted_step <= user.mfa_last_used_step:
            raise HTTPException(status_code=400, detail="El código MFA ya fue utilizado")
        user.mfa_last_used_step = accepted_step
    else:
        remaining, matched = mfa.consume_recovery_code(_recovery_codes(user.mfa_recovery_codes_encrypted), body.code)
        if not matched:
            raise HTTPException(status_code=400, detail="Código MFA inválido")
        user.mfa_recovery_codes_encrypted = json.dumps(remaining)

    user.mfa_challenge_hash = None
    user.mfa_challenge_expires_at = None
    await log_activity(
        db,
        action="MFA_LOGIN",
        entity_type="User",
        entity_id=user.id,
        user_id=user.id,
        company_id=user.company_id,
        details={"method": "totp" if accepted_step is not None else "recovery_code"},
    )
    await db.commit()
    return {"access_token": _token_for_user(user), "token_type": "bearer"}


@router.get("/login/mfa/status", response_model=MFAStatusResponse)
async def mfa_status(
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_superuser(current_user)
    return {
        "enabled": bool(current_user.mfa_enabled),
        "configured": bool(current_user.mfa_secret_encrypted),
        "recovery_codes_remaining": len(_recovery_codes(current_user.mfa_recovery_codes_encrypted)),
    }


@router.post("/login/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_superuser(current_user)
    if current_user.mfa_enabled:
        raise HTTPException(status_code=409, detail="MFA ya está habilitado; desactívalo antes de configurarlo de nuevo")

    secret = mfa.generate_totp_secret()
    current_user.mfa_secret_encrypted = secret
    current_user.mfa_recovery_codes_encrypted = None
    current_user.mfa_last_used_step = None
    current_user.mfa_challenge_hash = None
    current_user.mfa_challenge_expires_at = None
    await log_activity(
        db,
        action="MFA_SETUP_STARTED",
        entity_type="User",
        entity_id=current_user.id,
        user_id=current_user.id,
        company_id=current_user.company_id,
        details={"configured": True},
    )
    await db.commit()
    return {
        "enabled": False,
        "secret": secret,
        "otpauth_uri": mfa.build_totp_uri(secret, account=current_user.email),
    }


@router.post("/login/mfa/enable", response_model=MFAEnableResponse)
async def enable_mfa(
    body: MFACodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_superuser(current_user)
    result = await db.execute(select(User).where(User.id == current_user.id).with_for_update())
    user = result.scalars().first()
    if not user or user.mfa_enabled or not user.mfa_secret_encrypted:
        raise HTTPException(status_code=409, detail="Primero inicia una configuración de MFA pendiente")

    accepted_step = mfa.verify_totp(user.mfa_secret_encrypted, body.code)
    if accepted_step is None:
        raise HTTPException(status_code=400, detail="Código MFA inválido")

    recovery_codes = mfa.generate_recovery_codes()
    user.mfa_enabled = True
    user.mfa_enabled_at = datetime.now(timezone.utc)
    user.mfa_last_used_step = accepted_step
    user.mfa_recovery_codes_encrypted = json.dumps(recovery_codes)
    user.auth_token_version += 1
    await log_activity(
        db,
        action="MFA_ENABLED",
        entity_type="User",
        entity_id=user.id,
        user_id=user.id,
        company_id=user.company_id,
        details={"recovery_codes_issued": len(recovery_codes)},
    )
    await db.commit()
    return {"enabled": True, "recovery_codes": recovery_codes}


@router.post("/login/mfa/disable", response_model=MFAStatusResponse)
async def disable_mfa(
    body: MFACodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_superuser(current_user)
    result = await db.execute(select(User).where(User.id == current_user.id).with_for_update())
    user = result.scalars().first()
    if not user or not user.mfa_enabled:
        raise HTTPException(status_code=409, detail="MFA no está habilitado")
    accepted_step = mfa.verify_totp(user.mfa_secret_encrypted or "", body.code)
    if accepted_step is None:
        raise HTTPException(status_code=400, detail="Para desactivar MFA debes confirmar un código TOTP vigente")

    user.mfa_enabled = False
    user.mfa_secret_encrypted = None
    user.mfa_recovery_codes_encrypted = None
    user.mfa_last_used_step = None
    user.mfa_enabled_at = None
    user.mfa_challenge_hash = None
    user.mfa_challenge_expires_at = None
    user.auth_token_version += 1
    await log_activity(
        db,
        action="MFA_DISABLED",
        entity_type="User",
        entity_id=user.id,
        user_id=user.id,
        company_id=user.company_id,
        details={"sessions_revoked": True},
    )
    await db.commit()
    return {"enabled": False, "configured": False, "recovery_codes_remaining": 0}


@router.post("/login/sessions/revoke", response_model=Msg)
async def revoke_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Revoke every JWT currently issued for the authenticated account."""

    if get_impersonation_context():
        raise HTTPException(status_code=403, detail="No puedes revocar sesiones desde una sesión de soporte suplantada")
    current_user.auth_token_version += 1
    await log_activity(
        db,
        action="SESSIONS_REVOKED",
        entity_type="User",
        entity_id=current_user.id,
        user_id=current_user.id,
        company_id=current_user.company_id,
        details={"auth_token_version": current_user.auth_token_version},
    )
    await db.commit()
    return {"msg": "Todas las sesiones fueron revocadas. Inicia sesión nuevamente."}

from pydantic import EmailStr, Field

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

from app.services.email import EmailService
import jwt
from jwt.exceptions import PyJWTError

@router.post("/password-recovery/{email}", response_model=Msg)
@limiter.limit("3/minute")
async def recover_password(request: Request, email: str, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Password Recovery
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if user:
        # Generate Reset Token (Short lived, 1 hour)
        password_reset_token = create_access_token(
            data={"sub": user.email, "type": "reset"},
            expires_delta=timedelta(hours=1)
        )
        await EmailService.send_reset_password_email(email, password_reset_token)
        
    return {"msg": "If the email exists, a recovery email has been sent."}

@router.post("/reset-password", response_model=Msg)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    body: PasswordReset,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Reset Password
    """
    try:
        payload = jwt.decode(body.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        token_type = payload.get("type")
        
        if not email or token_type != "reset":
             raise HTTPException(status_code=400, detail="Invalid token")
             
    except (PyJWTError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid or expired token")
        
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    user.hashed_password = security.get_password_hash(body.new_password)
    user.auth_token_version += 1
    db.add(user)
    await db.commit()
    
    return {"msg": "Password updated successfully"}

from app.schemas.register import UserRegister
from app.models.company import Company
from app.models.branch import Branch
from app.models.warehouse import Warehouse
from sqlalchemy.exc import IntegrityError
from app.models.role import Role

@router.post("/register", response_model=Token)
@limiter.limit("5/minute")
async def register(
    request: Request,
    user_in: UserRegister,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Register a new user and company (Self-Service).
    """
    # 1. Check if user already exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
        
    # 2. Start Transaction
    try:
        # 1. Get Plan Duration (Safely)
        try:
            stmt = select(Plan).where(Plan.code == "FREE")
            result = await db.execute(stmt)
            plan_db = result.scalars().first()
            duration_days = plan_db.duration_days if plan_db else 30
        except Exception as e:
            print(f"Error fetching plan duration: {e}")
            duration_days = 30
            
        valid_until = datetime.utcnow() + timedelta(days=duration_days)

        # 2. Create Company
        company = Company(
            name=user_in.company_name,
            plan="FREE",
            valid_until=valid_until.isoformat(),
            is_active=True
        )
        db.add(company)
        await db.flush() # Get ID
        
        # 2. Create Default Branch
        branch = Branch(
            name="Principal",
            company_id=company.id,
            is_active=True
        )
        db.add(branch)
        await db.flush()
        db.add(Warehouse(
            branch_id=branch.id,
            name="Bodega principal",
            code="PRINCIPAL",
            is_default=True,
            allows_ecommerce=True,
            company_id=company.id,
        ))
        
        # 3. Create Admin Role for this Company
        # We must create a specific role for this new tenant
        role = Role(
            name="ADMINISTRADOR", 
            description="Administrador del sistema", 
            permissions={"all": True}, # Full permissions
            company_id=company.id
        )
        db.add(role)
        await db.flush() # Get Role ID

        # 4. Create User
        user = User(
            email=user_in.email,
            hashed_password=security.get_password_hash(user_in.password),
            full_name=f"{user_in.first_name} {user_in.last_name}",
            company_id=company.id,
            is_superuser=False,
            role_id=role.id, 
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Database integrity error")
    except Exception:
        await db.rollback()
        logger.exception("Registration failed")
        raise HTTPException(status_code=500, detail="Registration failed")

    # 3. Return Access Token (Auto Login)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": _token_for_user(user),
        "token_type": "bearer",
    }
