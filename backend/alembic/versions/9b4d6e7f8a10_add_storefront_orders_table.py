"""add_storefront_orders_table

Revision ID: 9b4d6e7f8a10
Revises: f4c2e9a1b6d0
Create Date: 2026-03-12 02:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9b4d6e7f8a10"
down_revision: Union[str, None] = "f4c2e9a1b6d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "storefront_orders",
        sa.Column("storefront_id", sa.UUID(), nullable=False),
        sa.Column("sale_id", sa.UUID(), nullable=False),
        sa.Column("customer_user_id", sa.UUID(), nullable=True),
        sa.Column("customer_name", sa.String(), nullable=False),
        sa.Column("customer_email", sa.String(), nullable=False),
        sa.Column("customer_phone", sa.String(), nullable=True),
        sa.Column("customer_document_id", sa.String(), nullable=True),
        sa.Column("shipping_line1", sa.String(), nullable=False),
        sa.Column("shipping_city", sa.String(), nullable=True),
        sa.Column("shipping_state", sa.String(), nullable=True),
        sa.Column("shipping_country", sa.String(), nullable=True),
        sa.Column("shipping_postal_code", sa.String(), nullable=True),
        sa.Column("coupon_code", sa.String(), nullable=True),
        sa.Column("buyer_note", sa.Text(), nullable=True),
        sa.Column("payment_provider", sa.String(), nullable=False),
        sa.Column("payment_status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("currency", sa.String(), nullable=False, server_default="USD"),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["customer_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"]),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sale_id", name="uq_storefront_order_sale"),
    )
    op.create_index(op.f("ix_storefront_orders_storefront_id"), "storefront_orders", ["storefront_id"], unique=False)
    op.create_index(op.f("ix_storefront_orders_sale_id"), "storefront_orders", ["sale_id"], unique=False)
    op.create_index(op.f("ix_storefront_orders_customer_user_id"), "storefront_orders", ["customer_user_id"], unique=False)
    op.create_index(op.f("ix_storefront_orders_customer_email"), "storefront_orders", ["customer_email"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_storefront_orders_customer_email"), table_name="storefront_orders")
    op.drop_index(op.f("ix_storefront_orders_customer_user_id"), table_name="storefront_orders")
    op.drop_index(op.f("ix_storefront_orders_sale_id"), table_name="storefront_orders")
    op.drop_index(op.f("ix_storefront_orders_storefront_id"), table_name="storefront_orders")
    op.drop_table("storefront_orders")
