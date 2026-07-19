import uuid
from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

class InventoryLocation(BaseModel):
    __tablename__='inventory_locations'
    __table_args__=(UniqueConstraint('branch_id','code',name='uq_inventory_location_branch_code'),)
    branch_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('branches.id'),index=True)
    name: Mapped[str]=mapped_column(String)
    code: Mapped[str]=mapped_column(String)
    location_type: Mapped[str]=mapped_column(String,default='STORAGE')
    is_dispatch_location: Mapped[bool]=mapped_column(Boolean,default=False)
    branch=relationship('Branch')
