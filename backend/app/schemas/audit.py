from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any

class AuditLogBase(BaseModel):
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class AuditUser(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class AuditLog(AuditLogBase):
    id: UUID
    user_id: Optional[UUID] = None
    user: Optional[AuditUser] = None
    company_id: Optional[UUID] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
