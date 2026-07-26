from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class StorefrontCustomerAccount(BaseModel):
    """Authentication identity for a customer of one storefront."""

    __tablename__ = "storefront_customer_accounts"

    storefront_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("storefronts.id"), nullable=False, index=True
    )
    client_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=True)

    storefront = relationship("Storefront")
    client = relationship("Client")

    __table_args__ = (
        UniqueConstraint(
            "storefront_id",
            "email",
            name="uq_storefront_customer_account_storefront_email",
        ),
    )
