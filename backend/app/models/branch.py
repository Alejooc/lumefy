from sqlalchemy import String, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid

class Branch(BaseModel):
    __tablename__ = "branches"

    name: Mapped[str] = mapped_column(String, index=True)
    code: Mapped[str] = mapped_column(String, index=True, nullable=True)
    address: Mapped[str] = mapped_column(String, nullable=True)
    phone: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=True)
    
    # Configuration
    is_warehouse: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_pos: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Override company_id to be explicit foreign key if needed, 
    # but BaseModel already has it. We just need to ensure the relationship works.
    
    # Relationships
    # company = relationship("Company", back_populates="branches")
