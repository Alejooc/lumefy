"""add storefront collection and product promotions.

Revision ID: gb6a7b8c9d0e1
Revises: ga5f6a7b8c9d0
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "gb6a7b8c9d0e1"
down_revision: Union[str, None] = "ga5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "storefront_promotions",
        sa.Column("storefront_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("collection_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published_product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("discount_percent", sa.Float(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["collection_id"], ["store_collections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["published_product_id"], ["published_products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("target_type IN ('COLLECTION', 'PRODUCT')", name="ck_storefront_promotion_target_type"),
        sa.CheckConstraint("discount_percent > 0 AND discount_percent <= 100", name="ck_storefront_promotion_discount_percent"),
        sa.CheckConstraint(
            "(target_type = 'COLLECTION' AND collection_id IS NOT NULL AND published_product_id IS NULL) OR "
            "(target_type = 'PRODUCT' AND collection_id IS NULL AND published_product_id IS NOT NULL)",
            name="ck_storefront_promotion_single_target",
        ),
    )
    op.create_index(op.f("ix_storefront_promotions_storefront_id"), "storefront_promotions", ["storefront_id"], unique=False)
    op.create_index(op.f("ix_storefront_promotions_collection_id"), "storefront_promotions", ["collection_id"], unique=False)
    op.create_index(op.f("ix_storefront_promotions_published_product_id"), "storefront_promotions", ["published_product_id"], unique=False)
    op.create_index(
        "ix_storefront_promotions_active_window",
        "storefront_promotions",
        ["storefront_id", "is_active", "is_enabled", "starts_at", "ends_at"],
        unique=False,
    )
    op.alter_column("storefront_promotions", "priority", server_default=None)
    op.alter_column("storefront_promotions", "is_enabled", server_default=None)
    op.alter_column("storefront_promotions", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_storefront_promotions_active_window", table_name="storefront_promotions")
    op.drop_index(op.f("ix_storefront_promotions_published_product_id"), table_name="storefront_promotions")
    op.drop_index(op.f("ix_storefront_promotions_collection_id"), table_name="storefront_promotions")
    op.drop_index(op.f("ix_storefront_promotions_storefront_id"), table_name="storefront_promotions")
    op.drop_table("storefront_promotions")
