from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import BaseModel

class Client(BaseModel):
    __tablename__ = "clients"

    name: Mapped[str] = mapped_column(String, index=True)
    tax_id: Mapped[str] = mapped_column(String, index=True, nullable=True) # RUC/DNI/NIT
    email: Mapped[str] = mapped_column(String, index=True, nullable=True)
    phone: Mapped[str] = mapped_column(String, nullable=True)
    address: Mapped[str] = mapped_column(String, nullable=True)
    
    # Notes or internal comments
    notes: Mapped[str] = mapped_column(String, nullable=True)
