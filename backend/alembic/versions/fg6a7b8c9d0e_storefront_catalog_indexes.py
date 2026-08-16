"""add indexes used by storefront catalog filters and stock checks

Revision ID: fg6a7b8c9d0e
Revises: ff5a6b7c8d9e
"""

from alembic import op


revision = "fg6a7b8c9d0e"
down_revision = "ff5a6b7c8d9e"
branch_labels = depends_on = None


def upgrade() -> None:
    # The public catalog checks a warehouse and product together. The
    # existing unique inventory index starts with company_id, so PostgreSQL
    # cannot use it efficiently for this storefront predicate.
    op.create_index(
        "ix_inventory_warehouse_product",
        "inventory",
        ["warehouse_id", "product_id"],
        unique=False,
    )
    # Category/brand/type are optional storefront filters and are not part of
    # the product model's existing company-prefixed indexes.
    op.create_index("ix_products_category_id", "products", ["category_id"], unique=False)
    op.create_index("ix_products_brand_id", "products", ["brand_id"], unique=False)
    op.create_index("ix_products_product_type", "products", ["product_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_products_product_type", table_name="products")
    op.drop_index("ix_products_brand_id", table_name="products")
    op.drop_index("ix_products_category_id", table_name="products")
    op.drop_index("ix_inventory_warehouse_product", table_name="inventory")
