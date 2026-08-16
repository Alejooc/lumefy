"""optimize product search, filters, and detail loading

Revision ID: ff5a6b7c8d9e
Revises: fe4f5a6b7c8d
"""

from alembic import op


revision = "ff5a6b7c8d9e"
down_revision = "fe4f5a6b7c8d"
branch_labels = depends_on = None


def upgrade() -> None:
    # PostgreSQL's trigram operator class makes the existing ILIKE '%term%'
    # searches index-backed instead of scanning the whole catalog.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    # The wrapper is explicitly immutable so PostgreSQL can use it in an
    # expression index while preserving the catalog's accent-insensitive
    # search behavior ("cafe" matches "Café").
    op.execute(
        """
        CREATE OR REPLACE FUNCTION lumefy_unaccent(text)
        RETURNS text
        LANGUAGE sql
        IMMUTABLE
        PARALLEL SAFE
        AS $$ SELECT unaccent($1) $$
        """
    )

    op.create_index(
        "ix_products_company_created_id",
        "products",
        ["company_id", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_products_company_category",
        "products",
        ["company_id", "category_id"],
        unique=False,
    )
    op.create_index(
        "ix_products_company_brand",
        "products",
        ["company_id", "brand_id"],
        unique=False,
    )
    op.create_index(
        "ix_products_company_type",
        "products",
        ["company_id", "product_type"],
        unique=False,
    )
    # selectinload(Product.images) filters on product_id; without this index
    # opening a product scans every image row in the tenant database.
    op.create_index(
        "ix_product_images_product_order",
        "product_images",
        ["product_id", "order"],
        unique=False,
    )
    op.create_index(
        "ix_published_products_storefront_status_product",
        "published_products",
        ["storefront_id", "is_published", "is_active", "product_id"],
        unique=False,
    )

    for table, column, name in (
        ("products", "name", "ix_products_name_trgm"),
        ("products", "sku", "ix_products_sku_trgm"),
        ("products", "barcode", "ix_products_barcode_trgm"),
        ("products", "internal_reference", "ix_products_internal_reference_trgm"),
        ("products", "description", "ix_products_description_trgm"),
        ("product_variants", "name", "ix_product_variants_name_trgm"),
        ("product_variants", "sku", "ix_product_variants_sku_trgm"),
        ("product_variants", "barcode", "ix_product_variants_barcode_trgm"),
        ("published_products", "custom_title", "ix_published_products_custom_title_trgm"),
        ("published_products", "custom_description", "ix_published_products_custom_description_trgm"),
        ("published_products", "slug", "ix_published_products_slug_trgm"),
    ):
        op.execute(
            f"CREATE INDEX {name} ON {table} USING gin ({column} gin_trgm_ops)"
        )

    for table, column, name in (
        ("products", "name", "ix_products_name_unaccent_trgm"),
        ("products", "sku", "ix_products_sku_unaccent_trgm"),
        ("products", "description", "ix_products_description_unaccent_trgm"),
        ("product_variants", "name", "ix_product_variants_name_unaccent_trgm"),
        ("product_variants", "sku", "ix_product_variants_sku_unaccent_trgm"),
        ("product_variants", "barcode", "ix_product_variants_barcode_unaccent_trgm"),
        ("published_products", "custom_title", "ix_published_products_custom_title_unaccent_trgm"),
        ("published_products", "custom_description", "ix_published_products_custom_description_unaccent_trgm"),
        ("published_products", "slug", "ix_published_products_slug_unaccent_trgm"),
    ):
        op.execute(
            f"CREATE INDEX {name} ON {table} USING gin "
            f"(lumefy_unaccent(lower({column})) gin_trgm_ops)"
        )


def downgrade() -> None:
    for name in (
        "ix_published_products_slug_unaccent_trgm",
        "ix_published_products_custom_description_unaccent_trgm",
        "ix_published_products_custom_title_unaccent_trgm",
        "ix_product_variants_barcode_unaccent_trgm",
        "ix_product_variants_sku_unaccent_trgm",
        "ix_product_variants_name_unaccent_trgm",
        "ix_products_description_unaccent_trgm",
        "ix_products_sku_unaccent_trgm",
        "ix_products_name_unaccent_trgm",
        "ix_product_variants_barcode_trgm",
        "ix_product_variants_sku_trgm",
        "ix_product_variants_name_trgm",
        "ix_published_products_slug_trgm",
        "ix_published_products_custom_description_trgm",
        "ix_published_products_custom_title_trgm",
        "ix_products_description_trgm",
        "ix_products_internal_reference_trgm",
        "ix_products_barcode_trgm",
        "ix_products_sku_trgm",
        "ix_products_name_trgm",
    ):
        op.execute(f"DROP INDEX IF EXISTS {name}")

    op.drop_index("ix_product_images_product_order", table_name="product_images")
    op.drop_index(
        "ix_published_products_storefront_status_product",
        table_name="published_products",
    )
    op.drop_index("ix_products_company_type", table_name="products")
    op.drop_index("ix_products_company_brand", table_name="products")
    op.drop_index("ix_products_company_category", table_name="products")
    op.drop_index("ix_products_company_created_id", table_name="products")
    op.execute("DROP FUNCTION IF EXISTS lumefy_unaccent(text)")
