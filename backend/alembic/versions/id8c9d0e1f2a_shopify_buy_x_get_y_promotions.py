"""add Buy X Get Y promotion rules.

Revision ID: id8c9d0e1f2a
Revises: hc7b8c9d0e1f
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "id8c9d0e1f2a"
down_revision: Union[str, None] = "hc7b8c9d0e1f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "storefront_promotions",
        sa.Column("promotion_type", sa.String(length=24), nullable=False, server_default="AMOUNT_OFF"),
    )
    op.add_column("storefront_promotions", sa.Column("reward_target_type", sa.String(length=16), nullable=True))
    op.add_column(
        "storefront_promotions",
        sa.Column("reward_collection_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "storefront_promotions",
        sa.Column("reward_published_product_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "storefront_promotions",
        sa.Column("buy_quantity", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "storefront_promotions",
        sa.Column("get_quantity", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "storefront_promotions",
        sa.Column("get_discount_type", sa.String(length=16), nullable=False, server_default="PERCENT"),
    )
    op.add_column(
        "storefront_promotions",
        sa.Column("get_discount_value", sa.Float(), nullable=False, server_default="100"),
    )
    op.create_foreign_key(
        "fk_storefront_promotion_reward_collection",
        "storefront_promotions",
        "store_collections",
        ["reward_collection_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_storefront_promotion_reward_published_product",
        "storefront_promotions",
        "published_products",
        ["reward_published_product_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_storefront_promotions_reward_collection_id",
        "storefront_promotions",
        ["reward_collection_id"],
        unique=False,
    )
    op.create_index(
        "ix_storefront_promotions_reward_published_product_id",
        "storefront_promotions",
        ["reward_published_product_id"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_storefront_promotion_promotion_type",
        "storefront_promotions",
        "promotion_type IN ('AMOUNT_OFF', 'BUY_X_GET_Y')",
    )
    op.create_check_constraint(
        "ck_storefront_promotion_buy_get_targets",
        "storefront_promotions",
        "promotion_type = 'AMOUNT_OFF' OR ("
        "target_type IN ('COLLECTION', 'PRODUCT') AND "
        "reward_target_type IN ('COLLECTION', 'PRODUCT') AND "
        "((reward_target_type = 'COLLECTION' AND reward_collection_id IS NOT NULL AND reward_published_product_id IS NULL) OR "
        "(reward_target_type = 'PRODUCT' AND reward_collection_id IS NULL AND reward_published_product_id IS NOT NULL)) AND "
        "buy_quantity > 0 AND get_quantity > 0)",
    )
    op.create_check_constraint(
        "ck_storefront_promotion_get_discount",
        "storefront_promotions",
        "get_discount_type IN ('PERCENT', 'FIXED') AND "
        "((get_discount_type = 'PERCENT' AND get_discount_value > 0 AND get_discount_value <= 100) OR "
        "(get_discount_type = 'FIXED' AND get_discount_value > 0))",
    )
    for column in ("promotion_type", "buy_quantity", "get_quantity", "get_discount_type", "get_discount_value"):
        op.alter_column("storefront_promotions", column, server_default=None)


def downgrade() -> None:
    op.drop_constraint("ck_storefront_promotion_get_discount", "storefront_promotions", type_="check")
    op.drop_constraint("ck_storefront_promotion_buy_get_targets", "storefront_promotions", type_="check")
    op.drop_constraint("ck_storefront_promotion_promotion_type", "storefront_promotions", type_="check")
    op.drop_index("ix_storefront_promotions_reward_published_product_id", table_name="storefront_promotions")
    op.drop_index("ix_storefront_promotions_reward_collection_id", table_name="storefront_promotions")
    op.drop_constraint("fk_storefront_promotion_reward_published_product", "storefront_promotions", type_="foreignkey")
    op.drop_constraint("fk_storefront_promotion_reward_collection", "storefront_promotions", type_="foreignkey")
    op.drop_column("storefront_promotions", "get_discount_value")
    op.drop_column("storefront_promotions", "get_discount_type")
    op.drop_column("storefront_promotions", "get_quantity")
    op.drop_column("storefront_promotions", "buy_quantity")
    op.drop_column("storefront_promotions", "reward_published_product_id")
    op.drop_column("storefront_promotions", "reward_collection_id")
    op.drop_column("storefront_promotions", "reward_target_type")
    op.drop_column("storefront_promotions", "promotion_type")
