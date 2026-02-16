from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class NotificationTemplateBase(BaseModel):
    code: str
    name: str
    type: str = "info" # info, success, warning, danger
    title_template: str
    body_template: str
    is_active: bool = True

class NotificationTemplateCreate(NotificationTemplateBase):
    pass

class NotificationTemplateUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    title_template: Optional[str] = None
    body_template: Optional[str] = None
    is_active: Optional[bool] = None

class NotificationTemplate(NotificationTemplateBase):
    id: UUID

    class Config:
        from_attributes = True

class ManualNotification(BaseModel):
    user_id: Optional[UUID] = None  # If None, send to all (broadcast) or filtered
    target_all: bool = False
    title: str
    message: str
    type: str = "info"
    link: Optional[str] = None
