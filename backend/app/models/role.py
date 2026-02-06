from sqlalchemy import String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

class Role(BaseModel):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    permissions: Mapped[dict] = mapped_column(JSON, default={})
    
    # Relationships
    # Relationships
    # users = relationship("User", back_populates="role")
