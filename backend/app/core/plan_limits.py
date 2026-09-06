"""
Plan enforcement dependency for FastAPI endpoints.

Usage:
    # Check subscription is valid (not expired)
    @router.post("/something")
    async def create_something(
        user: User = Depends(PlanLimitChecker())
    ):

    # Check a specific resource limit
    @router.post("/users")
    async def create_user(
        user: User = Depends(PlanLimitChecker(resource="users", count_model=User))
    ):
"""
from datetime import datetime, timezone
from typing import Optional, Type

from fastapi import Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core import auth
from app.models.user import User
from app.models.plan import Plan


def subscription_access_state(
    *,
    is_active: bool,
    subscription_status: str | None,
    valid_until: str | None,
    now: datetime | None = None,
) -> str:
    """Return the explicit access policy state for a tenant subscription.

    PAST_DUE is a short operational grace state only while its contracted
    expiry remains in the future. Unknown statuses and malformed dates fail
    closed so they cannot silently bypass subscription enforcement.
    """

    if not is_active:
        return "DISABLED"
    status = (subscription_status or "ACTIVE").strip().upper()
    if status not in {"ACTIVE", "PAST_DUE"}:
        return "SUSPENDED"
    if not valid_until:
        return status

    raw_expiry = str(valid_until).strip()
    try:
        expiry = datetime.fromisoformat(raw_expiry.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return "INVALID_EXPIRY"
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if len(raw_expiry) == 10 and "T" not in raw_expiry and " " not in raw_expiry:
        expiry = expiry.replace(hour=23, minute=59, second=59, microsecond=999999)
    reference_time = now or datetime.now(timezone.utc)
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)
    return "EXPIRED" if reference_time >= expiry else status


class PlanLimitChecker:
    """
    Dependency that:
    1. Checks if the company subscription is still valid (valid_until).
    2. Optionally checks a resource limit (e.g. max users, max products).
    """

    def __init__(self, resource: Optional[str] = None, count_model: Optional[Type] = None):
        """
        Args:
            resource: Key in Plan.limits dict, e.g. "users", "products", "branches"
            count_model: SQLAlchemy model to count for the company  (must have company_id)
        """
        self.resource = resource
        self.count_model = count_model

    async def __call__(
        self,
        user: User = Depends(auth.get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        # Superusers bypass all plan checks
        if user.is_superuser:
            return user

        if not user.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El usuario no tiene empresa asociada.",
            )

        # --- 1. Check subscription expiration ---
        from app.models.company import Company

        result = await db.execute(select(Company).where(Company.id == user.company_id))
        company = result.scalar_one_or_none()

        if not company:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La empresa no existe o está desactivada. Contacta soporte.",
            )

        access_state = subscription_access_state(
            is_active=bool(company.is_active),
            subscription_status=company.subscription_status,
            valid_until=company.valid_until,
        )
        if access_state == "DISABLED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La empresa está desactivada. Contacta soporte.",
            )
        if access_state in {"SUSPENDED", "INVALID_EXPIRY"}:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="La suscripción de la empresa no está activa. Contacta soporte.",
            )
        if access_state == "EXPIRED":
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Tu suscripción ha expirado. Renueva tu plan para continuar.",
            )

        # --- 2. Check resource limit (optional) ---
        if self.resource and self.count_model:
            plan_result = await db.execute(
                select(Plan).where(
                    func.upper(Plan.code) == (company.plan or "").strip().upper(),
                    Plan.is_active.is_(True),
                )
            )
            plan = plan_result.scalar_one_or_none()

            if not plan:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="El plan de la empresa no está configurado. Contacta soporte.",
                )

            if plan.limits:
                max_allowed = plan.limits.get(self.resource)
                if max_allowed is not None:
                    count_result = await db.execute(
                        select(func.count())
                        .select_from(self.count_model)
                        .where(self.count_model.company_id == user.company_id)
                    )
                    current_count = count_result.scalar() or 0

                    if current_count >= max_allowed:
                        raise HTTPException(
                            status_code=status.HTTP_402_PAYMENT_REQUIRED,
                            detail=f"Has alcanzado el límite de {max_allowed} {self.resource} de tu plan ({company.plan}). Actualiza tu plan para agregar más.",
                        )

        return user
