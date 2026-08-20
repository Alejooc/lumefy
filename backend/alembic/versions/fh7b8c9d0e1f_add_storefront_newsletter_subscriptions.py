"""add storefront newsletter subscriptions

Revision ID: fh7b8c9d0e1f
Revises: fg6a7b8c9d0e
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "fh7b8c9d0e1f"
down_revision = "fg6a7b8c9d0e"
branch_labels = depends_on = None


def upgrade() -> None:
    op.create_table(
        "storefront_newsletter_subscriptions",
        sa.Column("storefront_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="home"),
        sa.Column("subscribed_at", sa.DateTime(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "storefront_id",
            "email",
            name="uq_storefront_newsletter_storefront_email",
        ),
    )
    op.create_index(
        "ix_storefront_newsletter_subscriptions_email",
        "storefront_newsletter_subscriptions",
        ["email"],
        unique=False,
    )
    op.create_index(
        "ix_storefront_newsletter_subscriptions_storefront_id",
        "storefront_newsletter_subscriptions",
        ["storefront_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_storefront_newsletter_subscriptions_storefront_id",
        table_name="storefront_newsletter_subscriptions",
    )
    op.drop_index(
        "ix_storefront_newsletter_subscriptions_email",
        table_name="storefront_newsletter_subscriptions",
    )
    op.drop_table("storefront_newsletter_subscriptions")
