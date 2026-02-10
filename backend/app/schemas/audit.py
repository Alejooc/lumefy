from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any

class AuditLogBase(BaseModel):
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class AuditLog(AuditLogBase):
    id: UUID
    user_id: Optional[UUID] = None
    company_id: Optional[UUID] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
