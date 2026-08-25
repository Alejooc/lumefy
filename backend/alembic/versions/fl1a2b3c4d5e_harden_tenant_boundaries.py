"""backfill and enforce critical tenant boundaries.

Revision ID: fl1a2b3c4d5e
Revises: fk0d1e2f3a4b
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "fl1a2b3c4d5e"
down_revision = "fk0d1e2f3a4b"
branch_labels = depends_on = None


UUID = postgresql.UUID(as_uuid=True)


def _count(sql: str) -> int:
    return int(op.get_bind().execute(sa.text(sql)).scalar_one())


def _require_clean(label: str, sql: str) -> None:
    count = _count(sql)
    if count:
        raise RuntimeError(
            f"No se puede aplicar {revision}: {count} filas con aislamiento inconsistente en {label}. "
            "Corrige esas asociaciones y vuelve a ejecutar la migración."
        )


def _alter_company_not_null(table: str) -> None:
    op.alter_column(
        table,
        "company_id",
        existing_type=UUID,
        nullable=False,
    )


def _backfill_from_storefront(table: str) -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE {table} AS child
            SET company_id = storefront.company_id
            FROM storefronts AS storefront
            WHERE child.storefront_id = storefront.id
              AND child.company_id IS NULL
            """
        )
    )


def _backfill_from_source(table: str) -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE {table} AS child
            SET company_id = source.company_id
            FROM integration_sources AS source
            WHERE child.source_id = source.id
              AND child.company_id IS NULL
            """
        )
    )


def _backfill_from_pricelist(table: str) -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE {table} AS child
            SET company_id = pricelist.company_id
            FROM price_lists AS pricelist
            WHERE child.pricelist_id = pricelist.id
              AND child.company_id IS NULL
            """
        )
    )


def upgrade() -> None:
    # Variants inherit their tenant from the product. This is intentionally
    # fail-closed: an orphan or mismatched row must be reviewed before the
    # database starts enforcing the boundary.
    op.execute(
        sa.text(
            """
            UPDATE product_variants AS variant
            SET company_id = product.company_id
            FROM products AS product
            WHERE variant.product_id = product.id
              AND variant.company_id IS NULL
              AND product.company_id IS NOT NULL
            """
        )
    )
    _require_clean(
        "product_variants",
        """
        SELECT count(*)
        FROM product_variants AS variant
        LEFT JOIN products AS product ON product.id = variant.product_id
        WHERE variant.company_id IS NULL
           OR product.company_id IS NULL
           OR variant.company_id <> product.company_id
        """,
    )
    _alter_company_not_null("product_variants")
    op.create_index(
        "ix_product_variants_company_product",
        "product_variants",
        ["company_id", "product_id"],
        unique=False,
    )

    # Price lists are consumed by public storefronts, POS and checkout. Keep
    # their items, products, variants and external source inside one tenant.
    _require_clean("price_lists", "SELECT count(*) FROM price_lists WHERE company_id IS NULL")
    _alter_company_not_null("price_lists")
    _require_clean(
        "price_lists.source_id",
        """
        SELECT count(*)
        FROM price_lists AS pricelist
        JOIN integration_sources AS source ON source.id = pricelist.source_id
        WHERE pricelist.source_id IS NOT NULL
          AND (source.company_id IS NULL OR pricelist.company_id <> source.company_id)
        """,
    )
    _backfill_from_pricelist("pricelist_items")
    _require_clean("pricelist_items", "SELECT count(*) FROM pricelist_items WHERE company_id IS NULL")
    _require_clean(
        "pricelist_items.pricelist_id",
        """
        SELECT count(*)
        FROM pricelist_items AS item
        JOIN price_lists AS pricelist ON pricelist.id = item.pricelist_id
        WHERE item.company_id <> pricelist.company_id
        """,
    )
    _require_clean(
        "pricelist_items.product_id",
        """
        SELECT count(*)
        FROM pricelist_items AS item
        JOIN products AS product ON product.id = item.product_id
        WHERE product.company_id IS NULL
           OR item.company_id <> product.company_id
        """,
    )
    _require_clean(
        "pricelist_items.variant_id",
        """
        SELECT count(*)
        FROM pricelist_items AS item
        JOIN product_variants AS variant ON variant.id = item.variant_id
        WHERE item.variant_id IS NOT NULL
          AND (
              variant.company_id IS NULL
              OR item.company_id <> variant.company_id
              OR variant.product_id <> item.product_id
          )
        """,
    )
    _alter_company_not_null("pricelist_items")

    # Every storefront and every public storefront record must belong to a
    # company. The parent is the source of truth for historical rows.
    _require_clean("storefronts", "SELECT count(*) FROM storefronts WHERE company_id IS NULL")
    _alter_company_not_null("storefronts")
    _require_clean(
        "storefronts.price_list_id",
        """
        SELECT count(*)
        FROM storefronts AS storefront
        JOIN price_lists AS pricelist ON pricelist.id = storefront.price_list_id
        WHERE storefront.price_list_id IS NOT NULL
          AND storefront.company_id <> pricelist.company_id
        """,
    )
    storefront_children = (
        "storefront_domains",
        "store_collections",
        "published_products",
        "store_navigation_items",
        "store_payment_gateways",
        "storefront_shipping_destinations",
        "storefront_shipping_methods",
        "storefront_shipping_rules",
        "storefront_orders",
        "storefront_coupons",
        "storefront_customer_accounts",
        "storefront_newsletter_subscriptions",
    )
    for table in storefront_children:
        _backfill_from_storefront(table)
        _require_clean(table, f"SELECT count(*) FROM {table} WHERE company_id IS NULL")
        _require_clean(
            f"{table}.company_id",
            f"""
            SELECT count(*)
            FROM {table} AS child
            JOIN storefronts AS storefront ON storefront.id = child.storefront_id
            WHERE child.company_id <> storefront.company_id
            """,
        )
        _alter_company_not_null(table)

    op.execute(
        sa.text(
            """
            UPDATE store_collection_products AS link
            SET company_id = storefront.company_id
            FROM store_collections AS collection
            JOIN storefronts AS storefront ON storefront.id = collection.storefront_id
            WHERE link.collection_id = collection.id
              AND link.company_id IS NULL
            """
        )
    )
    _require_clean(
        "store_collection_products",
        "SELECT count(*) FROM store_collection_products WHERE company_id IS NULL",
    )
    _require_clean(
        "store_collection_products.company_id",
        """
        SELECT count(*)
        FROM store_collection_products AS link
        JOIN store_collections AS collection ON collection.id = link.collection_id
        WHERE link.company_id <> collection.company_id
        """,
    )
    _require_clean(
        "store_collection_products.published_product_id",
        """
        SELECT count(*)
        FROM store_collection_products AS link
        JOIN published_products AS published ON published.id = link.published_product_id
        WHERE link.company_id <> published.company_id
        """,
    )
    _alter_company_not_null("store_collection_products")

    _require_clean(
        "published_products.product_id",
        """
        SELECT count(*)
        FROM published_products AS published
        JOIN products AS product ON product.id = published.product_id
        WHERE product.company_id IS NULL
           OR published.company_id <> product.company_id
        """,
    )

    # Integration records inherit their tenant from the source. This closes
    # the same class of historical nulls in public proxy and sync paths.
    _require_clean(
        "integration_sources",
        "SELECT count(*) FROM integration_sources WHERE company_id IS NULL",
    )
    _alter_company_not_null("integration_sources")
    integration_children = (
        "integration_sync_runs",
        "integration_record_links",
        "integration_product_prices",
        "integration_webhook_events",
        "pricelist_source_rules",
    )
    for table in integration_children:
        _backfill_from_source(table)
        _require_clean(table, f"SELECT count(*) FROM {table} WHERE company_id IS NULL")
        _require_clean(
            f"{table}.company_id",
            f"""
            SELECT count(*)
            FROM {table} AS child
            JOIN integration_sources AS source ON source.id = child.source_id
            WHERE child.company_id <> source.company_id
            """,
        )
        _alter_company_not_null(table)

    _require_clean(
        "integration_record_links.local_product_id",
        """
        SELECT count(*)
        FROM integration_record_links AS link
        JOIN products AS product ON product.id = link.local_product_id
        WHERE link.local_product_id IS NOT NULL
          AND (product.company_id IS NULL OR link.company_id <> product.company_id)
        """,
    )
    _require_clean(
        "integration_record_links.local_variant_id",
        """
        SELECT count(*)
        FROM integration_record_links AS link
        JOIN product_variants AS variant ON variant.id = link.local_variant_id
        WHERE link.local_variant_id IS NOT NULL
          AND (variant.company_id IS NULL OR link.company_id <> variant.company_id)
        """,
    )
    _require_clean(
        "integration_product_prices.product_id",
        """
        SELECT count(*)
        FROM integration_product_prices AS price
        JOIN products AS product ON product.id = price.product_id
        WHERE product.company_id IS NULL
           OR price.company_id <> product.company_id
        """,
    )
    _require_clean(
        "integration_product_prices.variant_id",
        """
        SELECT count(*)
        FROM integration_product_prices AS price
        JOIN product_variants AS variant ON variant.id = price.variant_id
        WHERE price.variant_id IS NOT NULL
          AND (variant.company_id IS NULL OR price.company_id <> variant.company_id)
        """,
    )
    _require_clean(
        "pricelist_source_rules.pricelist_id",
        """
        SELECT count(*)
        FROM pricelist_source_rules AS rule
        JOIN price_lists AS price_list ON price_list.id = rule.pricelist_id
        WHERE price_list.company_id IS NULL
           OR rule.company_id <> price_list.company_id
        """,
    )

    # Composite foreign keys make the tenant relationship a database
    # invariant instead of relying only on endpoint filters.
    op.create_unique_constraint(
        "uq_products_id_company",
        "products",
        ["id", "company_id"],
    )
    op.create_unique_constraint(
        "uq_storefronts_id_company",
        "storefronts",
        ["id", "company_id"],
    )
    op.create_unique_constraint(
        "uq_store_collections_id_company",
        "store_collections",
        ["id", "company_id"],
    )
    op.create_unique_constraint(
        "uq_published_products_id_company",
        "published_products",
        ["id", "company_id"],
    )
    op.create_unique_constraint(
        "uq_integration_sources_id_company",
        "integration_sources",
        ["id", "company_id"],
    )
    op.create_unique_constraint(
        "uq_product_variants_id_company",
        "product_variants",
        ["id", "company_id"],
    )
    op.create_unique_constraint(
        "uq_price_lists_id_company",
        "price_lists",
        ["id", "company_id"],
    )
    op.create_unique_constraint(
        "uq_pricelist_items_id_company",
        "pricelist_items",
        ["id", "company_id"],
    )

    op.create_foreign_key(
        "fk_pricelist_items_pricelist_tenant",
        "pricelist_items",
        "price_lists",
        ["pricelist_id", "company_id"],
        ["id", "company_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_pricelist_items_product_tenant",
        "pricelist_items",
        "products",
        ["product_id", "company_id"],
        ["id", "company_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_pricelist_items_variant_tenant",
        "pricelist_items",
        "product_variants",
        ["variant_id", "company_id"],
        ["id", "company_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_storefronts_price_list_tenant",
        "storefronts",
        "price_lists",
        ["price_list_id", "company_id"],
        ["id", "company_id"],
    )

    op.create_foreign_key(
        "fk_product_variants_product_tenant",
        "product_variants",
        "products",
        ["product_id", "company_id"],
        ["id", "company_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_published_products_storefront_tenant",
        "published_products",
        "storefronts",
        ["storefront_id", "company_id"],
        ["id", "company_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_published_products_product_tenant",
        "published_products",
        "products",
        ["product_id", "company_id"],
        ["id", "company_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_store_collection_products_collection_tenant",
        "store_collection_products",
        "store_collections",
        ["collection_id", "company_id"],
        ["id", "company_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_store_collection_products_published_tenant",
        "store_collection_products",
        "published_products",
        ["published_product_id", "company_id"],
        ["id", "company_id"],
        ondelete="CASCADE",
    )
    for table in integration_children:
        op.create_foreign_key(
            f"fk_{table}_source_tenant",
            table,
            "integration_sources",
            ["source_id", "company_id"],
            ["id", "company_id"],
            ondelete="CASCADE",
        )
    op.create_foreign_key(
        "fk_integration_product_prices_product_tenant",
        "integration_product_prices",
        "products",
        ["product_id", "company_id"],
        ["id", "company_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_integration_product_prices_variant_tenant",
        "integration_product_prices",
        "product_variants",
        ["variant_id", "company_id"],
        ["id", "company_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    for table, constraint in (
        ("storefronts", "fk_storefronts_price_list_tenant"),
        ("pricelist_items", "fk_pricelist_items_variant_tenant"),
        ("pricelist_items", "fk_pricelist_items_product_tenant"),
        ("pricelist_items", "fk_pricelist_items_pricelist_tenant"),
    ):
        op.drop_constraint(constraint, table, type_="foreignkey")
    for table, constraint in (
        ("integration_product_prices", "fk_integration_product_prices_variant_tenant"),
        ("integration_product_prices", "fk_integration_product_prices_product_tenant"),
    ):
        op.drop_constraint(constraint, table, type_="foreignkey")
    for table in (
        "pricelist_source_rules",
        "integration_webhook_events",
        "integration_product_prices",
        "integration_record_links",
        "integration_sync_runs",
    ):
        op.drop_constraint(f"fk_{table}_source_tenant", table, type_="foreignkey")
    op.drop_constraint(
        "fk_store_collection_products_published_tenant",
        "store_collection_products",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_store_collection_products_collection_tenant",
        "store_collection_products",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_published_products_product_tenant",
        "published_products",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_published_products_storefront_tenant",
        "published_products",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_product_variants_product_tenant",
        "product_variants",
        type_="foreignkey",
    )
    for table, constraint in (
        ("integration_sources", "uq_integration_sources_id_company"),
        ("published_products", "uq_published_products_id_company"),
        ("store_collections", "uq_store_collections_id_company"),
        ("storefronts", "uq_storefronts_id_company"),
        ("products", "uq_products_id_company"),
        ("product_variants", "uq_product_variants_id_company"),
        ("pricelist_items", "uq_pricelist_items_id_company"),
        ("price_lists", "uq_price_lists_id_company"),
    ):
        op.drop_constraint(constraint, table, type_="unique")
    for table in (
        "pricelist_source_rules",
        "integration_webhook_events",
        "integration_product_prices",
        "integration_record_links",
        "integration_sync_runs",
        "integration_sources",
        "store_collection_products",
        "storefront_newsletter_subscriptions",
        "storefront_customer_accounts",
        "storefront_coupons",
        "storefront_orders",
        "storefront_shipping_rules",
        "storefront_shipping_methods",
        "storefront_shipping_destinations",
        "store_payment_gateways",
        "store_navigation_items",
        "published_products",
        "store_collections",
        "storefront_domains",
        "storefronts",
        "product_variants",
        "pricelist_items",
        "price_lists",
    ):
        op.alter_column(
            table,
            "company_id",
            existing_type=UUID,
            nullable=True,
        )
    op.drop_index("ix_product_variants_company_product", table_name="product_variants")
