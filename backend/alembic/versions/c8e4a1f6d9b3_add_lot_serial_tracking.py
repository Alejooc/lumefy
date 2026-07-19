"""add lot and serial tracking

Revision ID: c8e4a1f6d9b3
Revises: b9d3e5f7a2c4
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8e4a1f6d9b3"
down_revision: Union[str, None] = "b9d3e5f7a2c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("tracking_type", sa.String(), nullable=False, server_default="NONE"))
    op.create_table(
        "inventory_lots",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("branch_id", sa.UUID(), nullable=False),
        sa.Column("lot_number", sa.String(), nullable=True),
        sa.Column("serial_number", sa.String(), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("unit_cost", sa.Float(), nullable=False),
        sa.Column("source_reference", sa.String(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inventory_lots_product_id"), "inventory_lots", ["product_id"], unique=False)
    op.create_index(op.f("ix_inventory_lots_branch_id"), "inventory_lots", ["branch_id"], unique=False)
    op.create_index(op.f("ix_inventory_lots_lot_number"), "inventory_lots", ["lot_number"], unique=False)
    op.create_index(op.f("ix_inventory_lots_serial_number"), "inventory_lots", ["serial_number"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_inventory_lots_serial_number"), table_name="inventory_lots")
    op.drop_index(op.f("ix_inventory_lots_lot_number"), table_name="inventory_lots")
    op.drop_index(op.f("ix_inventory_lots_branch_id"), table_name="inventory_lots")
    op.drop_index(op.f("ix_inventory_lots_product_id"), table_name="inventory_lots")
    op.drop_table("inventory_lots")
    op.drop_column("products", "tracking_type")
