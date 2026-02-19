from sqlalchemy import String, Float, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import BaseModel

class Plan(BaseModel):
    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String, index=True)
    code: Mapped[str] = mapped_column(String, unique=True, index=True) # FREE, PRO, ENTERPRISE
    description: Mapped[str] = mapped_column(String, nullable=True)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String, default="USD")
    duration_days: Mapped[int] = mapped_column(default=30)
    button_text: Mapped[str] = mapped_column(String, nullable=True, default="Seleccionar Plan")
    
    # Features & Limits
    features: Mapped[dict] = mapped_column(JSON, default={}) # List of enabled features
    limits: Mapped[dict] = mapped_column(JSON, default={}) # {"users": 5, "companies": 1}
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True) # Visible on pricing page
