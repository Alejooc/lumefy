"""speed up storefront availability lookups

Revision ID: a3b4c5d6e7f8
Revises: a2b3c4d5e6f7
"""

from alembic import op


revision = "a3b4c5d6e7f8"
down_revision = "a2b3c4d5e6f7"
branch_labels = depends_on = None


def upgrade() -> None:
    # Storefront catalog requests constrain inventory by warehouse and product
    # (and then group product/variant rows in Python). The existing unique
    # identity index starts with company_id, so it cannot serve this lookup.
    op.create_index(
        "ix_inventory_warehouse_product_variant",
        "inventory",
        ["warehouse_id", "product_id", "variant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_inventory_warehouse_product_variant", table_name="inventory")
