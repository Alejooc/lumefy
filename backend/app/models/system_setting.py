from sqlalchemy import String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base # Using Base directly if BaseModel imposes UUID id which we might not want for Key
# Actually BaseModel uses UUID id. For settings, Key is better as PK or a slug.
# Let's use BaseModel and add a 'key' column with unique index, using UUID as internal ID is fine.
from app.models.base import BaseModel

class SystemSetting(BaseModel):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String, unique=True, index=True) # e.g. 'system_name', 'logo_url'
    value: Mapped[str] = mapped_column(Text, nullable=True)
    group: Mapped[str] = mapped_column(String, default="general") # general, branding, security
    is_public: Mapped[bool] = mapped_column(Boolean, default=False) # valid for unauth users
    description: Mapped[str] = mapped_column(String, nullable=True)
