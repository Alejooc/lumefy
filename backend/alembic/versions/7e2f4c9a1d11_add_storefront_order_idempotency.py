"""add_storefront_order_idempotency

Revision ID: 7e2f4c9a1d11
Revises: 9b4d6e7f8a10
Create Date: 2026-03-12 02:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7e2f4c9a1d11"
down_revision: Union[str, None] = "9b4d6e7f8a10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("storefront_orders", sa.Column("idempotency_key", sa.String(), nullable=True))
    op.create_index(op.f("ix_storefront_orders_idempotency_key"), "storefront_orders", ["idempotency_key"], unique=False)
    op.create_unique_constraint(
        "uq_storefront_order_storefront_idempotency",
        "storefront_orders",
        ["storefront_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_storefront_order_storefront_idempotency", "storefront_orders", type_="unique")
    op.drop_index(op.f("ix_storefront_orders_idempotency_key"), table_name="storefront_orders")
    op.drop_column("storefront_orders", "idempotency_key")
