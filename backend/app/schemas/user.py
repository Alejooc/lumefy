from typing import Optional
from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str
    company_id: Optional[UUID] = None
    role_id: Optional[UUID] = None

class UserUpdate(UserBase):
    password: Optional[str] = None

class User(UserBase):
    id: UUID
    company_id: Optional[UUID] = None
    role_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
