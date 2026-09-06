"""Persist the pending-payment deadline for storefront reservations."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fy3d4e5f6a7b"
down_revision: Union[str, None] = "fx2c3d4e5f6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "storefront_orders",
        sa.Column("payment_pending_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_storefront_orders_payment_pending_until",
        "storefront_orders",
        ["payment_pending_until"],
    )


def downgrade() -> None:
    op.drop_index("ix_storefront_orders_payment_pending_until", table_name="storefront_orders")
    op.drop_column("storefront_orders", "payment_pending_until")
