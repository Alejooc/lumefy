"""track variants in stock takes

Revision ID: fe4f5a6b7c8d
Revises: fd3e4f5a6b7c
"""

from alembic import op
import sqlalchemy as sa


revision = "fe4f5a6b7c8d"
down_revision = "fd3e4f5a6b7c"
branch_labels = depends_on = None


def upgrade() -> None:
    op.add_column("stock_take_items", sa.Column("variant_id", sa.UUID(), nullable=True))
    op.create_index("ix_stock_take_items_variant_id", "stock_take_items", ["variant_id"], unique=False)
    op.create_foreign_key(
        "fk_stock_take_items_variant_id_product_variants",
        "stock_take_items",
        "product_variants",
        ["variant_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_stock_take_items_variant_id_product_variants", "stock_take_items", type_="foreignkey")
    op.drop_index("ix_stock_take_items_variant_id", table_name="stock_take_items")
    op.drop_column("stock_take_items", "variant_id")
