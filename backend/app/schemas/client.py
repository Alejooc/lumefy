from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from uuid import UUID
from typing import List, Dict, Any, Optional
import enum
import re

CLIENT_STATUS_VALUES = ("active", "inactive", "prospective", "at_risk")
CLIENT_TAX_ID_PATTERN = re.compile(r"^[A-Za-z0-9 ./-]+$")
CLIENT_PHONE_PATTERN = re.compile(r"^[0-9()+ -]+$")


def _normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None

class ClientBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    tax_id: Optional[str] = Field(default=None, max_length=30)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=25)
    address: Optional[str] = Field(default=None, max_length=180)
    notes: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = True
    
    # CRM Fields
    status: str = Field(default="active")
    tags: Optional[Dict[str, Any]] = None
    last_interaction_at: Optional[datetime] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("Name must contain at least 2 characters")
        return normalized

    @field_validator("tax_id", "phone", "address", "notes", mode="before")
    @classmethod
    def normalize_optional_fields(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_optional_text(value)

    @field_validator("tax_id")
    @classmethod
    def validate_tax_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not CLIENT_TAX_ID_PATTERN.fullmatch(value):
            raise ValueError("Tax ID contains invalid characters")
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not CLIENT_PHONE_PATTERN.fullmatch(value):
            raise ValueError("Phone contains invalid characters")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in CLIENT_STATUS_VALUES:
            raise ValueError(f"Status must be one of: {', '.join(CLIENT_STATUS_VALUES)}")
        return normalized

class ClientCreate(ClientBase):
    credit_limit: Optional[float] = Field(default=0.0, ge=0, le=999999999)

class ClientUpdate(ClientBase):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    credit_limit: Optional[float] = Field(default=None, ge=0, le=999999999)
    status: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None

class Client(ClientBase):
    id: UUID
    company_id: UUID
    credit_limit: float
    current_balance: float
    created_at: datetime
    updated_at: datetime
    
    # New relationships or counts can go here
    activity_count: Optional[int] = 0
    total_sales: Optional[float] = 0.0

    class Config:
        from_attributes = True

# CRM Activities
class ActivityType(str, enum.Enum):
    CALL = "CALL"
    MEETING = "MEETING"
    EMAIL = "EMAIL"
    NOTE = "NOTE"
    SYSTEM = "SYSTEM"

class ActivityBase(BaseModel):
    type: ActivityType
    content: str = Field(..., min_length=3, max_length=500)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("Content must contain at least 3 characters")
        return normalized

class ActivityCreate(ActivityBase):
    pass

class Activity(ActivityBase):
    id: UUID
    client_id: UUID
    user_id: UUID
    created_at: datetime
    user_name: Optional[str] = None

    class Config:
        from_attributes = True

class ClientStats(BaseModel):
    total_sales: float = 0.0
    order_count: int = 0
    average_order_value: float = 0.0
    last_sale_at: Optional[datetime] = None
    
class UnifiedTimelineItem(BaseModel):
    id: UUID
    type: str # ACTIVITY, LEDGER
    category: str # CALL, NOTE, CHARGE, PAYMENT etc.
    content: str
    amount: Optional[float] = None
    created_at: datetime
    user_name: Optional[str] = None



