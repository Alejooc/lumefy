from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base

class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String, unique=True, index=True, nullable=False) # e.g. 'NEW_SALE', 'WELCOME'
    name = Column(String, nullable=False)
    type = Column(String, default="info") # info, success, warning, danger
    title_template = Column(String, nullable=False)
    body_template = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
