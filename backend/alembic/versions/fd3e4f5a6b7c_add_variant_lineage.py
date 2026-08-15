"""track selected variants on sales and inventory movements

Revision ID: fd3e4f5a6b7c
Revises: fc2d3e4f5a6b
"""

from alembic import op
import sqlalchemy as sa


revision = "fd3e4f5a6b7c"
down_revision = "fc2d3e4f5a6b"
branch_labels = depends_on = None


def upgrade() -> None:
    op.add_column("sale_items", sa.Column("variant_id", sa.UUID(), nullable=True))
    op.create_index("ix_sale_items_variant_id", "sale_items", ["variant_id"], unique=False)
    op.create_foreign_key(
        "fk_sale_items_variant_id_product_variants",
        "sale_items",
        "product_variants",
        ["variant_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("inventory_movements", sa.Column("variant_id", sa.UUID(), nullable=True))
    op.create_index("ix_inventory_movements_variant_id", "inventory_movements", ["variant_id"], unique=False)
    op.create_foreign_key(
        "fk_inventory_movements_variant_id_product_variants",
        "inventory_movements",
        "product_variants",
        ["variant_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_inventory_movements_variant_id_product_variants", "inventory_movements", type_="foreignkey")
    op.drop_index("ix_inventory_movements_variant_id", table_name="inventory_movements")
    op.drop_column("inventory_movements", "variant_id")
    op.drop_constraint("fk_sale_items_variant_id_product_variants", "sale_items", type_="foreignkey")
    op.drop_index("ix_sale_items_variant_id", table_name="sale_items")
    op.drop_column("sale_items", "variant_id")
