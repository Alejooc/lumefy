from typing import Optional
from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from app.schemas.role import Role # Added Import

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False

class UserCreate(UserBase):
    password: str
    company_id: Optional[UUID] = None
    role_id: Optional[UUID] = None

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    role_id: Optional[UUID] = None

class User(UserBase):
    id: UUID
    company_id: Optional[UUID] = None
    role_id: Optional[UUID] = None
    role: Optional[Role] = None # Added Role object
    is_superuser: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
