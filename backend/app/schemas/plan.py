from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

# Shared properties
class PlanBase(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = 0.0
    currency: Optional[str] = "USD"
    duration_days: Optional[int] = 30
    features: Optional[Any] = [] # Can be Dict (legacy) or List[str] (new)
    limits: Optional[Dict[str, Any]] = {}
    is_active: Optional[bool] = True
    is_public: Optional[bool] = True

# Properties to receive on creation
class PlanCreate(PlanBase):
    name: str
    code: str

# Properties to receive on update
class PlanUpdate(PlanBase):
    pass

# Properties shared by models stored in DB
class PlanInDBBase(PlanBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Properties to return to client
class Plan(PlanInDBBase):
    pass
