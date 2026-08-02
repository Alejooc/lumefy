"""add storefront destinations, shipping methods and rules

Revision ID: b2c3d4e5f6a7
Revises: f8b9c0d1e2f3
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "f8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "storefront_shipping_destinations",
        sa.Column("storefront_id", sa.UUID(), nullable=False),
        sa.Column("country_code", sa.String(length=8), nullable=False, server_default="CO"),
        sa.Column("state_code", sa.String(length=32), nullable=True),
        sa.Column("state_name", sa.String(length=120), nullable=False),
        sa.Column("city_code", sa.String(length=32), nullable=True),
        sa.Column("city_name", sa.String(length=120), nullable=True),
        sa.Column("destination_type", sa.String(length=20), nullable=False, server_default="city"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "storefront_id",
            "country_code",
            "state_code",
            "city_code",
            name="uq_storefront_shipping_destination_codes",
        ),
    )
    op.create_index(
        "ix_storefront_shipping_destinations_storefront_id",
        "storefront_shipping_destinations",
        ["storefront_id"],
    )

    op.create_table(
        "storefront_shipping_methods",
        sa.Column("storefront_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("method_type", sa.String(length=20), nullable=False, server_default="delivery"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimate_min_days", sa.Integer(), nullable=True),
        sa.Column("estimate_max_days", sa.Integer(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storefront_id", "code", name="uq_storefront_shipping_method_code"),
    )
    op.create_index(
        "ix_storefront_shipping_methods_storefront_id",
        "storefront_shipping_methods",
        ["storefront_id"],
    )

    op.create_table(
        "storefront_shipping_rules",
        sa.Column("storefront_id", sa.UUID(), nullable=False),
        sa.Column("method_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("destination_type", sa.String(length=20), nullable=False, server_default="global"),
        sa.Column("country_code", sa.String(length=8), nullable=True),
        sa.Column("state_code", sa.String(length=32), nullable=True),
        sa.Column("state_name", sa.String(length=120), nullable=True),
        sa.Column("city_code", sa.String(length=32), nullable=True),
        sa.Column("city_name", sa.String(length=120), nullable=True),
        sa.Column("payment_provider", sa.String(length=80), nullable=True),
        sa.Column("min_subtotal", sa.Float(), nullable=True),
        sa.Column("max_subtotal", sa.Float(), nullable=True),
        sa.Column("min_weight", sa.Float(), nullable=True),
        sa.Column("max_weight", sa.Float(), nullable=True),
        sa.Column("charge_type", sa.String(length=20), nullable=False, server_default="flat"),
        sa.Column("amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rate_per_kg", sa.Float(), nullable=False, server_default="0"),
        sa.Column("estimate_min_days", sa.Integer(), nullable=True),
        sa.Column("estimate_max_days", sa.Integer(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["method_id"], ["storefront_shipping_methods.id"]),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_storefront_shipping_rules_storefront_id",
        "storefront_shipping_rules",
        ["storefront_id"],
    )
    op.create_index(
        "ix_storefront_shipping_rules_method_id",
        "storefront_shipping_rules",
        ["method_id"],
    )

    op.add_column("storefront_orders", sa.Column("shipping_state_code", sa.String(length=32), nullable=True))
    op.add_column("storefront_orders", sa.Column("shipping_city_code", sa.String(length=32), nullable=True))
    op.add_column("storefront_orders", sa.Column("shipping_method_id", sa.UUID(), nullable=True))
    op.add_column("storefront_orders", sa.Column("shipping_method_name", sa.String(length=120), nullable=True))
    op.add_column("storefront_orders", sa.Column("shipping_rule_name", sa.String(length=120), nullable=True))
    op.add_column("storefront_orders", sa.Column("shipping_weight", sa.Float(), nullable=True))
    op.add_column("storefront_orders", sa.Column("shipping_quote_required", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_storefront_orders_shipping_method_id", "storefront_orders", ["shipping_method_id"])


def downgrade() -> None:
    op.drop_index("ix_storefront_orders_shipping_method_id", table_name="storefront_orders")
    op.drop_column("storefront_orders", "shipping_quote_required")
    op.drop_column("storefront_orders", "shipping_weight")
    op.drop_column("storefront_orders", "shipping_rule_name")
    op.drop_column("storefront_orders", "shipping_method_name")
    op.drop_column("storefront_orders", "shipping_method_id")
    op.drop_column("storefront_orders", "shipping_city_code")
    op.drop_column("storefront_orders", "shipping_state_code")
    op.drop_index("ix_storefront_shipping_rules_method_id", table_name="storefront_shipping_rules")
    op.drop_index("ix_storefront_shipping_rules_storefront_id", table_name="storefront_shipping_rules")
    op.drop_table("storefront_shipping_rules")
    op.drop_index("ix_storefront_shipping_methods_storefront_id", table_name="storefront_shipping_methods")
    op.drop_table("storefront_shipping_methods")
    op.drop_index("ix_storefront_shipping_destinations_storefront_id", table_name="storefront_shipping_destinations")
    op.drop_table("storefront_shipping_destinations")
