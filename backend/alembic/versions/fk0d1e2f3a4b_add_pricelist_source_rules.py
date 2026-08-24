"""add supplier-specific sale price rules"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "fk0d1e2f3a4b"
down_revision = "fj9b0c1d2e3f"
branch_labels = depends_on = None


def upgrade() -> None:
    op.create_table(
        "pricelist_source_rules",
        sa.Column("pricelist_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pricing_mode", sa.String(length=30), nullable=False, server_default="MARKUP_PERCENT"),
        sa.Column("base_source", sa.String(length=30), nullable=False, server_default="EXTERNAL_PRICE"),
        sa.Column("adjustment_value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rounding_step", sa.Float(), nullable=False, server_default="0"),
        sa.Column("min_margin_percent", sa.Float(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["pricelist_id"], ["price_lists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["integration_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pricelist_id", "source_id", name="uq_pricelist_source_rule"),
    )
    op.create_index("ix_pricelist_source_rules_pricelist", "pricelist_source_rules", ["pricelist_id"])
    op.create_index("ix_pricelist_source_rules_source", "pricelist_source_rules", ["source_id"])


def downgrade() -> None:
    op.drop_index("ix_pricelist_source_rules_source", table_name="pricelist_source_rules")
    op.drop_index("ix_pricelist_source_rules_pricelist", table_name="pricelist_source_rules")
    op.drop_table("pricelist_source_rules")
