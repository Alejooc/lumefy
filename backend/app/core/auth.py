from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_db
from app.schemas.token import TokenPayload
from app.models.user import User
from app.models.storefront_customer import StorefrontCustomerAccount
from app.core.audit import set_impersonation_context

import logging

logger = logging.getLogger(__name__)

# Preview sessions are intentionally limited to templates that have a public
# renderer. Keeping this allow-list here prevents a signed token from opening
# an arbitrary theme document through the public storefront endpoints.
SUPPORTED_STOREFRONT_PREVIEW_TEMPLATES = {"home", "product", "collection", "search", "cart", "pages"}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/login/access-token")
optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token",
    auto_error=False,
)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def get_storefront_preview_claims(token: str) -> tuple[UUID, UUID, str] | None:
    """Return the scoped claims of a temporary storefront preview session."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("scope") != "storefront_theme_preview":
            return None
        storefront_id = UUID(str(payload.get("storefront_id")))
        company_id = UUID(str(payload.get("company_id")))
        template_key = str(payload.get("template_key") or "")
        if template_key not in SUPPORTED_STOREFRONT_PREVIEW_TEMPLATES:
            return None
        return storefront_id, company_id, template_key
    except (PyJWTError, ValueError, TypeError, AttributeError):
        return None

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    set_impersonation_context(None)
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
    except (PyJWTError, AttributeError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.email == token_data.sub))
    user = result.scalars().first()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")

    # Tokens issued after the MFA/session-revocation migration carry the
    # user's current version. Once MFA is enabled, legacy tokens without a
    # version are rejected so enabling MFA cannot leave an old session open.
    token_version = payload.get("auth_version")
    if getattr(user, "mfa_enabled", False) and token_version is None:
        raise credentials_exception
    if token_version is not None:
        try:
            if int(token_version) != int(getattr(user, "auth_token_version", 0) or 0):
                raise credentials_exception
        except (TypeError, ValueError):
            raise credentials_exception

    if payload.get("scope") == "impersonation":
        operator_id = payload.get("impersonated_by_user_id")
        session_id = payload.get("impersonation_session_id")
        started_at = payload.get("impersonation_started_at")
        reason = payload.get("impersonation_reason")
        if operator_id and session_id and started_at and reason:
            set_impersonation_context({
                "operator_user_id": str(operator_id),
                "target_user_id": str(user.id),
                "target_company_id": str(user.company_id) if user.company_id else None,
                "session_id": str(session_id),
                "started_at": str(started_at),
                "reason": str(reason),
            })
    return user


async def get_current_storefront_customer(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> StorefrontCustomerAccount:
    """Resolve a public storefront token without touching internal users."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate storefront credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("scope") != "storefront":
            raise credentials_exception
        account_id = payload.get("customer_account_id") or payload.get("sub")
        storefront_id = payload.get("storefront_id")
        if not account_id or not storefront_id:
            raise credentials_exception
        account_uuid = UUID(str(account_id))
        storefront_uuid = UUID(str(storefront_id))
    except (PyJWTError, ValueError, TypeError):
        raise credentials_exception

    result = await db.execute(
        select(StorefrontCustomerAccount).where(
            StorefrontCustomerAccount.id == account_uuid,
            StorefrontCustomerAccount.storefront_id == storefront_uuid,
            StorefrontCustomerAccount.is_active == True,
        )
    )
    account = result.scalars().first()
    if account is None:
        raise credentials_exception
    return account


async def get_optional_current_storefront_customer(
    token: str | None = Depends(optional_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> StorefrontCustomerAccount | None:
    """Resolve a storefront customer when a checkout sends its session token."""
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("scope") != "storefront":
            return None
        account_id = payload.get("customer_account_id") or payload.get("sub")
        storefront_id = payload.get("storefront_id")
        if not account_id or not storefront_id:
            return None
        account_uuid = UUID(str(account_id))
        storefront_uuid = UUID(str(storefront_id))
    except (PyJWTError, ValueError, TypeError):
        return None

    result = await db.execute(
        select(StorefrontCustomerAccount).where(
            StorefrontCustomerAccount.id == account_uuid,
            StorefrontCustomerAccount.storefront_id == storefront_uuid,
            StorefrontCustomerAccount.is_active == True,
        )
    )
    return result.scalars().first()
