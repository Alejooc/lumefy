"""add_storefront_foundation

Revision ID: f4c2e9a1b6d0
Revises: c4f8a2b7d3e1
Create Date: 2026-02-28 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f4c2e9a1b6d0"
down_revision: Union[str, None] = "c4f8a2b7d3e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "storefronts",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("subdomain", sa.String(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("theme_key", sa.String(), nullable=False),
        sa.Column("theme_settings", sa.JSON(), nullable=False),
        sa.Column("checkout_settings", sa.JSON(), nullable=False),
        sa.Column("seo_settings", sa.JSON(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "slug", name="uq_storefront_company_slug"),
        sa.UniqueConstraint("subdomain", name="uq_storefront_subdomain"),
    )
    op.create_index(op.f("ix_storefronts_slug"), "storefronts", ["slug"], unique=False)
    op.create_index(op.f("ix_storefronts_subdomain"), "storefronts", ["subdomain"], unique=False)

    op.create_table(
        "storefront_domains",
        sa.Column("storefront_id", sa.UUID(), nullable=False),
        sa.Column("domain", sa.String(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain", name="uq_storefront_domain_domain"),
    )
    op.create_index(op.f("ix_storefront_domains_domain"), "storefront_domains", ["domain"], unique=False)
    op.create_index(op.f("ix_storefront_domains_storefront_id"), "storefront_domains", ["storefront_id"], unique=False)

    op.create_table(
        "store_collections",
        sa.Column("storefront_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("is_visible", sa.Boolean(), nullable=False),
        sa.Column("is_featured", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storefront_id", "slug", name="uq_store_collection_storefront_slug"),
    )
    op.create_index(op.f("ix_store_collections_slug"), "store_collections", ["slug"], unique=False)
    op.create_index(op.f("ix_store_collections_storefront_id"), "store_collections", ["storefront_id"], unique=False)

    op.create_table(
        "published_products",
        sa.Column("storefront_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("custom_title", sa.String(), nullable=True),
        sa.Column("custom_description", sa.Text(), nullable=True),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("price_override", sa.Float(), nullable=True),
        sa.Column("compare_at_price", sa.Float(), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("is_featured", sa.Boolean(), nullable=False),
        sa.Column("show_stock", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("seo_title", sa.String(), nullable=True),
        sa.Column("seo_description", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storefront_id", "product_id", name="uq_published_product_storefront_product"),
        sa.UniqueConstraint("storefront_id", "slug", name="uq_published_product_storefront_slug"),
    )
    op.create_index(op.f("ix_published_products_product_id"), "published_products", ["product_id"], unique=False)
    op.create_index(op.f("ix_published_products_slug"), "published_products", ["slug"], unique=False)
    op.create_index(op.f("ix_published_products_storefront_id"), "published_products", ["storefront_id"], unique=False)

    op.create_table(
        "store_navigation_items",
        sa.Column("storefront_id", sa.UUID(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("item_type", sa.String(), nullable=False),
        sa.Column("reference_id", sa.UUID(), nullable=True),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_visible", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["store_navigation_items.id"]),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_store_navigation_items_storefront_id"), "store_navigation_items", ["storefront_id"], unique=False)

    op.create_table(
        "store_payment_gateways",
        sa.Column("storefront_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("is_sandbox", sa.Boolean(), nullable=False),
        sa.Column("public_key", sa.String(), nullable=True),
        sa.Column("secret_key_encrypted", sa.String(), nullable=True),
        sa.Column("merchant_id", sa.String(), nullable=True),
        sa.Column("extra_config", sa.JSON(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storefront_id", "provider", name="uq_store_payment_gateway_storefront_provider"),
    )
    op.create_index(op.f("ix_store_payment_gateways_provider"), "store_payment_gateways", ["provider"], unique=False)
    op.create_index(op.f("ix_store_payment_gateways_storefront_id"), "store_payment_gateways", ["storefront_id"], unique=False)

    op.create_table(
        "store_collection_products",
        sa.Column("collection_id", sa.UUID(), nullable=False),
        sa.Column("published_product_id", sa.UUID(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["collection_id"], ["store_collections.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["published_product_id"], ["published_products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("collection_id", "published_product_id", name="uq_store_collection_product_pair"),
    )
    op.create_index(op.f("ix_store_collection_products_collection_id"), "store_collection_products", ["collection_id"], unique=False)
    op.create_index(op.f("ix_store_collection_products_published_product_id"), "store_collection_products", ["published_product_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_store_collection_products_published_product_id"), table_name="store_collection_products")
    op.drop_index(op.f("ix_store_collection_products_collection_id"), table_name="store_collection_products")
    op.drop_table("store_collection_products")

    op.drop_index(op.f("ix_store_payment_gateways_storefront_id"), table_name="store_payment_gateways")
    op.drop_index(op.f("ix_store_payment_gateways_provider"), table_name="store_payment_gateways")
    op.drop_table("store_payment_gateways")

    op.drop_index(op.f("ix_store_navigation_items_storefront_id"), table_name="store_navigation_items")
    op.drop_table("store_navigation_items")

    op.drop_index(op.f("ix_published_products_storefront_id"), table_name="published_products")
    op.drop_index(op.f("ix_published_products_slug"), table_name="published_products")
    op.drop_index(op.f("ix_published_products_product_id"), table_name="published_products")
    op.drop_table("published_products")

    op.drop_index(op.f("ix_store_collections_storefront_id"), table_name="store_collections")
    op.drop_index(op.f("ix_store_collections_slug"), table_name="store_collections")
    op.drop_table("store_collections")

    op.drop_index(op.f("ix_storefront_domains_storefront_id"), table_name="storefront_domains")
    op.drop_index(op.f("ix_storefront_domains_domain"), table_name="storefront_domains")
    op.drop_table("storefront_domains")

    op.drop_index(op.f("ix_storefronts_subdomain"), table_name="storefronts")
    op.drop_index(op.f("ix_storefronts_slug"), table_name="storefronts")
    op.drop_table("storefronts")
