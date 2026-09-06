"""Track the financial completion of approved returns."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fz4e5f6a7b8c"
down_revision: Union[str, None] = "fy3d4e5f6a7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "return_orders",
        sa.Column("refund_status", sa.String(length=30), nullable=False, server_default="NOT_REQUIRED"),
    )
    op.add_column("return_orders", sa.Column("refund_method", sa.String(length=30), nullable=True))
    op.add_column("return_orders", sa.Column("refund_reference", sa.String(length=160), nullable=True))
    op.add_column("return_orders", sa.Column("refund_processed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "return_orders",
        sa.Column("refund_processed_by", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_return_orders_refund_processed_by_users",
        "return_orders",
        "users",
        ["refund_processed_by"],
        ["id"],
    )
    op.create_index("ix_return_orders_refund_status", "return_orders", ["refund_status"])
    op.alter_column("return_orders", "refund_status", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_return_orders_refund_status", table_name="return_orders")
    op.drop_constraint("fk_return_orders_refund_processed_by_users", "return_orders", type_="foreignkey")
    op.drop_column("return_orders", "refund_processed_by")
    op.drop_column("return_orders", "refund_processed_at")
    op.drop_column("return_orders", "refund_reference")
    op.drop_column("return_orders", "refund_method")
    op.drop_column("return_orders", "refund_status")
