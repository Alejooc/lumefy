from sqlalchemy import String, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid
# Import Role to ensure visibility for relationship mapping
from app.models.role import Role
print("DEBUG: User Model Loaded")

class User(BaseModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    full_name: Mapped[str] = mapped_column(String, nullable=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=True)
    
    # Relationships
    # Relationships
    role = relationship(Role, lazy="joined")
    # company = relationship("Company", back_populates="users")
