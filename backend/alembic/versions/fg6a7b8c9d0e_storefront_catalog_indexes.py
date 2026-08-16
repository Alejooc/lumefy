"""add indexes used by storefront catalog filters

Revision ID: fg6a7b8c9d0e
Revises: a3b4c5d6e7f8
"""

from alembic import op


revision = "fg6a7b8c9d0e"
down_revision = "a3b4c5d6e7f8"
branch_labels = depends_on = None


def upgrade() -> None:
    # Category/brand/type are optional storefront filters and are not part of
    # the product model's existing company-prefixed indexes.
    op.create_index("ix_products_category_id", "products", ["category_id"], unique=False)
    op.create_index("ix_products_brand_id", "products", ["brand_id"], unique=False)
    op.create_index("ix_products_product_type", "products", ["product_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_products_product_type", table_name="products")
    op.drop_index("ix_products_brand_id", table_name="products")
    op.drop_index("ix_products_category_id", table_name="products")
