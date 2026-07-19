from typing import List
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.manufacturing import ManufacturingStatus

class BomLineIn(BaseModel):
    component_id: UUID
    quantity: float = Field(gt=0)
class BomIn(BaseModel):
    product_id: UUID
    quantity: float = Field(default=1, gt=0)
    lines: List[BomLineIn]
class BomOut(BomIn):
    id: UUID
    class Config: from_attributes = True
class ManufacturingOrderIn(BaseModel):
    bom_id: UUID
    branch_id: UUID
    quantity: float = Field(gt=0)
class ManufacturingOrderOut(ManufacturingOrderIn):
    id: UUID
    status: ManufacturingStatus
    class Config: from_attributes = True
