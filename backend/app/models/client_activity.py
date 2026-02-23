from sqlalchemy import String, ForeignKey, Text, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid
import enum
from datetime import datetime

class ActivityType(str, enum.Enum):
    CALL = "CALL"
    MEETING = "MEETING"
    EMAIL = "EMAIL"
    NOTE = "NOTE"
    SYSTEM = "SYSTEM"

class ClientActivity(BaseModel):
    __tablename__ = "client_activities"

    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    
    type: Mapped[ActivityType] = mapped_column(Enum(ActivityType), default=ActivityType.NOTE)
    content: Mapped[str] = mapped_column(Text)
    
    # Relationships
    client = relationship("Client", back_populates="activities")
    user = relationship("User")
