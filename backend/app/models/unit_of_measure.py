from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

class UnitOfMeasure(BaseModel):
    __tablename__ = "units_of_measure"

    name: Mapped[str] = mapped_column(String, index=True)  # Kg, Unidad, Litro, Metro, Caja
    abbreviation: Mapped[str] = mapped_column(String(10), nullable=True)  # kg, ud, L, m, cj
