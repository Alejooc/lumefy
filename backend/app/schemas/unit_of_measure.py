from typing import Optional
from pydantic import BaseModel
from uuid import UUID

class UnitOfMeasureBase(BaseModel):
    name: str
    abbreviation: Optional[str] = None

class UnitOfMeasureCreate(UnitOfMeasureBase):
    pass

class UnitOfMeasureUpdate(BaseModel):
    name: Optional[str] = None
    abbreviation: Optional[str] = None

class UnitOfMeasure(UnitOfMeasureBase):
    id: UUID
    company_id: Optional[UUID] = None

    class Config:
        from_attributes = True
