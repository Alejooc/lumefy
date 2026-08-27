"""add idempotent external order links and sale origin metadata.

Revision ID: fq5e6f7a8b9c
Revises: fp4d5e6f7a8b
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fq5e6f7a8b9c"
down_revision: Union[str, None] = "fp4d5e6f7a8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sales",
        sa.Column("origin_channel", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "sales",
        sa.Column("integration_source_id", sa.UUID(), nullable=True),
    )
    op.create_index("ix_sales_origin_channel", "sales", ["origin_channel"], unique=False)
    op.create_index("ix_sales_integration_source_id", "sales", ["integration_source_id"], unique=False)
    op.create_foreign_key(
        "fk_sales_integration_source_id",
        "sales",
        "integration_sources",
        ["integration_source_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "integration_order_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("sale_id", sa.UUID(), nullable=True),
        sa.Column("external_order_id", sa.String(length=255), nullable=False),
        sa.Column("external_number", sa.String(length=255), nullable=True),
        sa.Column("direction", sa.String(length=20), nullable=False, server_default="INBOUND"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING_MAPPING"),
        sa.Column("provider_status", sa.String(length=120), nullable=True),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("imported_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["integration_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "external_order_id", name="uq_integration_order_external"),
    )
    op.create_index("ix_integration_order_links_source_id", "integration_order_links", ["source_id"], unique=False)
    op.create_index("ix_integration_order_links_sale_id", "integration_order_links", ["sale_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_integration_order_links_sale_id", table_name="integration_order_links")
    op.drop_index("ix_integration_order_links_source_id", table_name="integration_order_links")
    op.drop_table("integration_order_links")
    op.drop_constraint("fk_sales_integration_source_id", "sales", type_="foreignkey")
    op.drop_index("ix_sales_integration_source_id", table_name="sales")
    op.drop_index("ix_sales_origin_channel", table_name="sales")
    op.drop_column("sales", "integration_source_id")
    op.drop_column("sales", "origin_channel")
