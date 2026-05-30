from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from uuid import UUID

class LedgerEntryBase(BaseModel):
    partner_id: UUID
    partner_type: str
    type: str # CHARGE, PAYMENT, REFUND, ADJUSTMENT
    amount: float
    balance_after: float
    reference_id: Optional[str] = None
    description: str

class LedgerEntry(LedgerEntryBase):
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True

class StatementResponse(BaseModel):
    current_balance: float
    credit_limit: float
    entries: List[LedgerEntry]

class PaymentRequest(BaseModel):
    amount: float = Field(..., gt=0, le=999999999)
    description: str = Field(..., min_length=3, max_length=160)
    reference_id: Optional[str] = Field(default=None, max_length=80)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("Description must contain at least 3 characters")
        return normalized

    @field_validator("reference_id", mode="before")
    @classmethod
    def normalize_reference_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None
