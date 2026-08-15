"""add company integration sources and sync history

Revision ID: f9a0b1c2d3e4
Revises: f8b9c0d1e2f3
"""

from alembic import op
import sqlalchemy as sa


revision = "f9a0b1c2d3e4"
down_revision = "f8b9c0d1e2f3"
branch_labels = depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_sources",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("provider_key", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("base_url", sa.String(), nullable=False),
        sa.Column("auth_type", sa.String(length=50), nullable=False),
        sa.Column("credentials", sa.JSON(), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("last_tested_at", sa.DateTime(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("last_sync_status", sa.String(length=30), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_integration_sources_company_id", "integration_sources", ["company_id"])

    op.create_table(
        "integration_sync_runs",
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("triggered_by_user_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("products_processed", sa.Integer(), nullable=False),
        sa.Column("products_created", sa.Integer(), nullable=False),
        sa.Column("products_updated", sa.Integer(), nullable=False),
        sa.Column("inventory_processed", sa.Integer(), nullable=False),
        sa.Column("inventory_updated", sa.Integer(), nullable=False),
        sa.Column("items_failed", sa.Integer(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["integration_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_integration_sync_runs_source_id", "integration_sync_runs", ["source_id"])

    op.create_table(
        "integration_record_links",
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("external_sku", sa.String(length=255), nullable=True),
        sa.Column("local_product_id", sa.UUID(), nullable=True),
        sa.Column("local_variant_id", sa.UUID(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["local_product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["local_variant_id"], ["product_variants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["integration_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "entity_type", "external_id", name="uq_integration_record_external"),
    )
    op.create_index("ix_integration_record_links_source_id", "integration_record_links", ["source_id"])
    op.create_index("ix_integration_record_links_external_sku", "integration_record_links", ["external_sku"])
    op.create_index("ix_integration_record_links_local_product_id", "integration_record_links", ["local_product_id"])
    op.create_index("ix_integration_record_links_local_variant_id", "integration_record_links", ["local_variant_id"])


def downgrade() -> None:
    op.drop_table("integration_record_links")
    op.drop_table("integration_sync_runs")
    op.drop_table("integration_sources")
