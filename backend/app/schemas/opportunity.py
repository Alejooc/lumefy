from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.opportunity import OpportunityStage


class OpportunityBase(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    client_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None
    expected_revenue: float = Field(default=0, ge=0)
    probability: float = Field(default=0, ge=0, le=100)
    expected_close_date: Optional[date] = None
    contact_name: Optional[str] = Field(default=None, max_length=120)
    contact_email: Optional[str] = Field(default=None, max_length=120)
    contact_phone: Optional[str] = Field(default=None, max_length=30)
    notes: Optional[str] = Field(default=None, max_length=2000)


class OpportunityCreate(OpportunityBase):
    stage: OpportunityStage = OpportunityStage.NEW


class OpportunityUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=160)
    client_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None
    stage: Optional[OpportunityStage] = None
    expected_revenue: Optional[float] = Field(default=None, ge=0)
    probability: Optional[float] = Field(default=None, ge=0, le=100)
    expected_close_date: Optional[date] = None
    contact_name: Optional[str] = Field(default=None, max_length=120)
    contact_email: Optional[str] = Field(default=None, max_length=120)
    contact_phone: Optional[str] = Field(default=None, max_length=30)
    notes: Optional[str] = Field(default=None, max_length=2000)
    lost_reason: Optional[str] = Field(default=None, max_length=500)


class OpportunityOut(OpportunityBase):
    id: UUID
    stage: OpportunityStage
    lost_reason: Optional[str] = None
    client_name: Optional[str] = None
    owner_name: Optional[str] = None

    class Config:
        from_attributes = True
