from typing import Optional, List
from pydantic import BaseModel
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
    amount: float
    description: str
    reference_id: Optional[str] = None
