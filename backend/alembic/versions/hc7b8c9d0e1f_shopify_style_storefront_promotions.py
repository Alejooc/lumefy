"""extend storefront promotions with Shopify-style configuration.

Revision ID: hc7b8c9d0e1f
Revises: gb6a7b8c9d0e1
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "hc7b8c9d0e1f"
down_revision: Union[str, None] = "gb6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_storefront_promotion_target_type",
        "storefront_promotions",
        type_="check",
    )
    op.drop_constraint(
        "ck_storefront_promotion_discount_percent",
        "storefront_promotions",
        type_="check",
    )
    op.drop_constraint(
        "ck_storefront_promotion_single_target",
        "storefront_promotions",
        type_="check",
    )

    op.add_column(
        "storefront_promotions",
        sa.Column("method", sa.String(length=16), nullable=False, server_default="AUTOMATIC"),
    )
    op.add_column("storefront_promotions", sa.Column("code", sa.String(length=80), nullable=True))
    op.add_column(
        "storefront_promotions",
        sa.Column("discount_type", sa.String(length=20), nullable=False, server_default="PERCENT"),
    )
    op.add_column(
        "storefront_promotions",
        sa.Column("discount_value", sa.Float(), nullable=True),
    )
    op.add_column(
        "storefront_promotions",
        sa.Column("minimum_requirement", sa.String(length=16), nullable=False, server_default="NONE"),
    )
    op.add_column(
        "storefront_promotions",
        sa.Column("minimum_amount", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "storefront_promotions",
        sa.Column("minimum_quantity", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("storefront_promotions", sa.Column("usage_limit", sa.Integer(), nullable=True))
    op.add_column(
        "storefront_promotions",
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "storefront_promotions",
        sa.Column("once_per_customer", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "storefront_promotions",
        sa.Column("combines_with_product", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "storefront_promotions",
        sa.Column("combines_with_order", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "storefront_promotions",
        sa.Column("combines_with_shipping", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "storefront_promotions",
        sa.Column("customer_eligibility", sa.String(length=24), nullable=False, server_default="ALL"),
    )

    op.execute(
        sa.text(
            "UPDATE storefront_promotions "
            "SET discount_value = discount_percent, minimum_amount = 0, "
            "minimum_quantity = 0, usage_count = 0"
        )
    )
    op.alter_column("storefront_promotions", "discount_value", nullable=False)
    op.alter_column("storefront_promotions", "discount_percent", nullable=True)

    op.create_index(
        "ix_storefront_promotions_storefront_code",
        "storefront_promotions",
        ["storefront_id", "code"],
        unique=True,
    )
    op.create_check_constraint(
        "ck_storefront_promotion_method",
        "storefront_promotions",
        "method IN ('AUTOMATIC', 'CODE')",
    )
    op.create_check_constraint(
        "ck_storefront_promotion_target_type",
        "storefront_promotions",
        "target_type IN ('COLLECTION', 'PRODUCT', 'ORDER', 'SHIPPING')",
    )
    op.create_check_constraint(
        "ck_storefront_promotion_discount_value",
        "storefront_promotions",
        "(discount_type = 'PERCENT' AND discount_value > 0 AND discount_value <= 100) OR "
        "(discount_type = 'FIXED' AND discount_value > 0) OR "
        "(discount_type = 'FREE_SHIPPING' AND discount_value >= 0)",
    )
    op.create_check_constraint(
        "ck_storefront_promotion_discount_type",
        "storefront_promotions",
        "discount_type IN ('PERCENT', 'FIXED', 'FREE_SHIPPING')",
    )
    op.create_check_constraint(
        "ck_storefront_promotion_requirement",
        "storefront_promotions",
        "minimum_requirement IN ('NONE', 'AMOUNT', 'QUANTITY') AND minimum_amount >= 0 AND minimum_quantity >= 0",
    )
    op.create_check_constraint(
        "ck_storefront_promotion_single_target_v2",
        "storefront_promotions",
        "((target_type = 'COLLECTION' AND collection_id IS NOT NULL AND published_product_id IS NULL) OR "
        "(target_type = 'PRODUCT' AND collection_id IS NULL AND published_product_id IS NOT NULL) OR "
        "(target_type IN ('ORDER', 'SHIPPING') AND collection_id IS NULL AND published_product_id IS NULL))",
    )

    for column in (
        "method",
        "discount_type",
        "minimum_requirement",
        "minimum_amount",
        "minimum_quantity",
        "usage_count",
        "once_per_customer",
        "combines_with_product",
        "combines_with_order",
        "combines_with_shipping",
        "customer_eligibility",
    ):
        op.alter_column("storefront_promotions", column, server_default=None)


def downgrade() -> None:
    op.drop_constraint("ck_storefront_promotion_single_target_v2", "storefront_promotions", type_="check")
    op.drop_constraint("ck_storefront_promotion_requirement", "storefront_promotions", type_="check")
    op.drop_constraint("ck_storefront_promotion_discount_type", "storefront_promotions", type_="check")
    op.drop_constraint("ck_storefront_promotion_discount_value", "storefront_promotions", type_="check")
    op.drop_constraint("ck_storefront_promotion_target_type", "storefront_promotions", type_="check")
    op.drop_constraint("ck_storefront_promotion_method", "storefront_promotions", type_="check")
    op.drop_index("ix_storefront_promotions_storefront_code", table_name="storefront_promotions")
    op.drop_column("storefront_promotions", "customer_eligibility")
    op.drop_column("storefront_promotions", "combines_with_shipping")
    op.drop_column("storefront_promotions", "combines_with_order")
    op.drop_column("storefront_promotions", "combines_with_product")
    op.drop_column("storefront_promotions", "once_per_customer")
    op.drop_column("storefront_promotions", "usage_count")
    op.drop_column("storefront_promotions", "usage_limit")
    op.drop_column("storefront_promotions", "minimum_quantity")
    op.drop_column("storefront_promotions", "minimum_amount")
    op.drop_column("storefront_promotions", "minimum_requirement")
    op.drop_column("storefront_promotions", "discount_value")
    op.drop_column("storefront_promotions", "discount_type")
    op.drop_column("storefront_promotions", "code")
    op.drop_column("storefront_promotions", "method")
    op.create_check_constraint(
        "ck_storefront_promotion_target_type",
        "storefront_promotions",
        "target_type IN ('COLLECTION', 'PRODUCT')",
    )
    op.create_check_constraint(
        "ck_storefront_promotion_discount_percent",
        "storefront_promotions",
        "discount_percent > 0 AND discount_percent <= 100",
    )
    op.create_check_constraint(
        "ck_storefront_promotion_single_target",
        "storefront_promotions",
        "(target_type = 'COLLECTION' AND collection_id IS NOT NULL AND published_product_id IS NULL) OR "
        "(target_type = 'PRODUCT' AND collection_id IS NULL AND published_product_id IS NOT NULL)",
    )
