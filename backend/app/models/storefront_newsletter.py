from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class StorefrontNewsletterSubscription(BaseModel):
    """A marketing opt-in scoped to a single storefront."""

    __tablename__ = "storefront_newsletter_subscriptions"

    storefront_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("storefronts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="home")
    subscribed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    storefront = relationship("Storefront")

    __table_args__ = (
        UniqueConstraint(
            "storefront_id",
            "email",
            name="uq_storefront_newsletter_storefront_email",
        ),
    )
