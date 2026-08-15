"""add variant inventory and integration attributes

Revision ID: fb1c2d3e4f5a
Revises: fa0b1c2d3e4f
"""

from alembic import op
import sqlalchemy as sa


revision = "fb1c2d3e4f5a"
down_revision = "fa0b1c2d3e4f"
branch_labels = depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("attributes", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("product_variants", sa.Column("price", sa.Float(), nullable=True))
    op.add_column("product_variants", sa.Column("cost", sa.Float(), nullable=True))
    op.add_column("product_variants", sa.Column("attributes", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("inventory", sa.Column("variant_id", sa.UUID(), nullable=True))
    op.create_index("ix_inventory_variant_id", "inventory", ["variant_id"], unique=False)
    op.create_foreign_key(
        "fk_inventory_variant_id_product_variants",
        "inventory",
        "product_variants",
        ["variant_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column("products", "attributes", server_default=None)
    op.alter_column("product_variants", "attributes", server_default=None)


def downgrade() -> None:
    op.drop_constraint("fk_inventory_variant_id_product_variants", "inventory", type_="foreignkey")
    op.drop_index("ix_inventory_variant_id", table_name="inventory")
    op.drop_column("inventory", "variant_id")
    op.drop_column("product_variants", "attributes")
    op.drop_column("product_variants", "cost")
    op.drop_column("product_variants", "price")
    op.drop_column("products", "attributes")
