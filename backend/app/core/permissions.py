from typing import List, Callable
from fastapi import Depends, HTTPException, status
from app.models.user import User
from app.core import auth

class PermissionChecker:
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    def __call__(self, user: User = Depends(auth.get_current_user)) -> User:
        # Platform administrators manage the SaaS through its dedicated API.
        # They must not access a tenant's operational data without an
        # impersonated, company-scoped session.
        if user.is_superuser:
            if self.required_permission == "manage_saas":
                return user
            if not user.company_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Platform administrators cannot access company-scoped operations directly"
                )
            return user

        # SaaS administration exposes global tenant data and is never delegated
        # through a company role, including roles with the local "all" shortcut.
        if self.required_permission == "manage_saas":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted. Required permission: manage_saas"
            )

        # Admin role has all permissions
        if user.role and user.role.permissions and user.role.permissions.get("all"):
            return user
            
        # Check specific permission
        if not user.role or not user.role.permissions or not user.role.permissions.get(self.required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required permission: {self.required_permission}"
            )
        return user
