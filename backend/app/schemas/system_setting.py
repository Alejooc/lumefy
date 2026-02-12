from typing import Optional, List
from pydantic import BaseModel
import uuid

class SystemSettingBase(BaseModel):
    key: str
    value: Optional[str] = None
    group: Optional[str] = "general"
    is_public: Optional[bool] = False
    description: Optional[str] = None

class SystemSettingCreate(SystemSettingBase):
    pass

class SystemSettingUpdate(BaseModel):
    value: str

class SystemSetting(SystemSettingBase):
    id: uuid.UUID

    class Config:
        from_attributes = True
