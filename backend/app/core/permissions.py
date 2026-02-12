from typing import List, Callable
from fastapi import Depends, HTTPException, status
from app.models.user import User
from app.core import auth

class PermissionChecker:
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    def __call__(self, user: User = Depends(auth.get_current_user)) -> User:
        # Superuser has all permissions
        if user.is_superuser:
            return user

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
