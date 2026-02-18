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
from datetime import datetime
from typing import Optional, Type

from fastapi import Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core import auth
from app.models.user import User
from app.models.plan import Plan


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

        if not company or not company.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La empresa está desactivada. Contacta soporte.",
            )

        if company.valid_until:
            try:
                expiry = datetime.fromisoformat(company.valid_until)
                if datetime.utcnow() > expiry:
                    raise HTTPException(
                        status_code=status.HTTP_402_PAYMENT_REQUIRED,
                        detail="Tu suscripción ha expirado. Renueva tu plan para continuar.",
                    )
            except ValueError:
                pass  # Malformed date — skip check rather than block

        # --- 2. Check resource limit (optional) ---
        if self.resource and self.count_model:
            plan_result = await db.execute(
                select(Plan).where(Plan.code == company.plan, Plan.is_active == True)
            )
            plan = plan_result.scalar_one_or_none()

            if plan and plan.limits:
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
