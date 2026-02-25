from datetime import datetime
import enum
import uuid

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class POSSessionStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class POSSession(BaseModel):
    __tablename__ = "pos_sessions"

    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    status: Mapped[POSSessionStatus] = mapped_column(Enum(POSSessionStatus), default=POSSessionStatus.OPEN, index=True)

    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    opening_amount: Mapped[float] = mapped_column(Float, default=0.0)
    counted_amount: Mapped[float] = mapped_column(Float, default=0.0)
    expected_amount: Mapped[float] = mapped_column(Float, default=0.0)
    over_short: Mapped[float] = mapped_column(Float, default=0.0)
    closing_note: Mapped[str] = mapped_column(String, nullable=True)

    branch = relationship("Branch")
    user = relationship("User")

