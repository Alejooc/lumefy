"""add external price snapshots and sales pricing engine

Revision ID: fj9b0c1d2e3f
Revises: fi8a9b0c1d2e
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "fj9b0c1d2e3f"
down_revision = "fi8a9b0c1d2e"
branch_labels = depends_on = None


def upgrade() -> None:
    op.add_column("price_lists", sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("price_lists", sa.Column("pricing_mode", sa.String(length=30), nullable=False, server_default="FIXED"))
    op.add_column("price_lists", sa.Column("base_source", sa.String(length=30), nullable=False, server_default="INTERNAL_PRICE"))
    op.add_column("price_lists", sa.Column("adjustment_value", sa.Float(), nullable=False, server_default="0"))
    op.add_column("price_lists", sa.Column("rounding_step", sa.Float(), nullable=False, server_default="0"))
    op.add_column("price_lists", sa.Column("min_margin_percent", sa.Float(), nullable=True))
    op.create_index("ix_price_lists_source_id", "price_lists", ["source_id"])
    op.create_foreign_key(
        "fk_price_lists_source_id", "price_lists", "integration_sources", ["source_id"], ["id"], ondelete="SET NULL"
    )

    op.add_column("pricelist_items", sa.Column("variant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.alter_column("pricelist_items", "price", existing_type=sa.Float(), nullable=True)
    op.create_index("ix_pricelist_items_variant_id", "pricelist_items", ["variant_id"])
    op.create_index(
        "ix_pricelist_items_product_variant",
        "pricelist_items",
        ["pricelist_id", "product_id", "variant_id"],
    )
    op.create_foreign_key(
        "fk_pricelist_items_variant_id", "pricelist_items", "product_variants", ["variant_id"], ["id"], ondelete="CASCADE"
    )
    op.create_unique_constraint(
        "uq_pricelist_item_variant", "pricelist_items", ["pricelist_id", "product_id", "variant_id"]
    )

    op.add_column("storefronts", sa.Column("price_list_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_storefronts_price_list_id", "storefronts", ["price_list_id"])
    op.create_foreign_key(
        "fk_storefronts_price_list_id", "storefronts", "price_lists", ["price_list_id"], ["id"], ondelete="SET NULL"
    )

    op.create_table(
        "integration_product_prices",
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=20), nullable=False, server_default="product"),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("external_price", sa.Float(), nullable=True),
        sa.Column("external_cost", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("synced_at", sa.DateTime(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["integration_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "entity_type", "external_id", name="uq_integration_product_price_external"),
    )
    op.create_index("ix_integration_product_prices_source_id", "integration_product_prices", ["source_id"])
    op.create_index("ix_integration_product_prices_product_id", "integration_product_prices", ["product_id"])
    op.create_index("ix_integration_product_prices_variant_id", "integration_product_prices", ["variant_id"])


def downgrade() -> None:
    op.drop_index("ix_integration_product_prices_variant_id", table_name="integration_product_prices")
    op.drop_index("ix_integration_product_prices_product_id", table_name="integration_product_prices")
    op.drop_index("ix_integration_product_prices_source_id", table_name="integration_product_prices")
    op.drop_table("integration_product_prices")

    op.drop_constraint("fk_storefronts_price_list_id", "storefronts", type_="foreignkey")
    op.drop_index("ix_storefronts_price_list_id", table_name="storefronts")
    op.drop_column("storefronts", "price_list_id")

    op.drop_constraint("uq_pricelist_item_variant", "pricelist_items", type_="unique")
    op.drop_constraint("fk_pricelist_items_variant_id", "pricelist_items", type_="foreignkey")
    op.drop_index("ix_pricelist_items_product_variant", table_name="pricelist_items")
    op.drop_index("ix_pricelist_items_variant_id", table_name="pricelist_items")
    op.drop_column("pricelist_items", "variant_id")
    op.alter_column("pricelist_items", "price", existing_type=sa.Float(), nullable=False)

    op.drop_constraint("fk_price_lists_source_id", "price_lists", type_="foreignkey")
    op.drop_index("ix_price_lists_source_id", table_name="price_lists")
    for column in ("min_margin_percent", "rounding_step", "adjustment_value", "base_source", "pricing_mode", "source_id"):
        op.drop_column("price_lists", column)
