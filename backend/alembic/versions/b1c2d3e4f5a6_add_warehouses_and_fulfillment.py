"""add warehouses and ecommerce fulfillment source

Revision ID: b1c2d3e4f5a6
Revises: f0a1b2c3d4e5
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "f0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "warehouses",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("allows_ecommerce", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=True),
        sa.UniqueConstraint("branch_id", "code", name="uq_warehouse_branch_code"),
    )
    op.create_index("ix_warehouses_branch_id", "warehouses", ["branch_id"])

    for table in ("inventory", "inventory_movements", "inventory_locations", "sales"):
        op.add_column(table, sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(f"fk_{table}_warehouse_id", table, "warehouses", ["warehouse_id"], ["id"])
        op.create_index(f"ix_{table}_warehouse_id", table, ["warehouse_id"])
    for table in ("storefronts", "storefront_orders"):
        op.add_column(table, sa.Column("fulfillment_warehouse_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(f"fk_{table}_fulfillment_warehouse_id", table, "warehouses", ["fulfillment_warehouse_id"], ["id"])
        op.create_index(f"ix_{table}_fulfillment_warehouse_id", table, ["fulfillment_warehouse_id"])

    # Every legacy branch becomes a commercial site with one compatible
    # default warehouse. Existing balances and movement history keep their
    # values and simply gain that physical source.
    op.execute("""
        INSERT INTO warehouses (id, branch_id, name, code, is_default, allows_ecommerce, company_id, created_at, updated_at, is_active)
        SELECT gen_random_uuid(), b.id, 'Bodega principal', 'PRINCIPAL', true, true, b.company_id, now(), now(), true
        FROM branches b
        WHERE NOT EXISTS (SELECT 1 FROM warehouses w WHERE w.branch_id = b.id AND w.is_default = true)
    """)
    for table in ("inventory", "inventory_movements", "inventory_locations", "sales"):
        op.execute(f"""
            UPDATE {table} t SET warehouse_id = w.id
            FROM warehouses w
            WHERE w.branch_id = t.branch_id AND w.is_default = true AND t.warehouse_id IS NULL
        """)
    op.execute("""
        UPDATE storefronts s
        SET fulfillment_warehouse_id = (
            SELECT w.id FROM warehouses w
            WHERE w.company_id = s.company_id AND w.is_default = true AND w.allows_ecommerce = true
            ORDER BY w.created_at ASC LIMIT 1
        )
        WHERE s.fulfillment_warehouse_id IS NULL
    """)
    op.execute("""
        UPDATE storefront_orders so SET fulfillment_warehouse_id = s.warehouse_id
        FROM sales s
        WHERE s.id = so.sale_id AND so.fulfillment_warehouse_id IS NULL
    """)


def downgrade() -> None:
    for table in ("storefront_orders", "storefronts"):
        op.drop_index(f"ix_{table}_fulfillment_warehouse_id", table_name=table)
        op.drop_constraint(f"fk_{table}_fulfillment_warehouse_id", table, type_="foreignkey")
        op.drop_column(table, "fulfillment_warehouse_id")
    for table in ("sales", "inventory_locations", "inventory_movements", "inventory"):
        op.drop_index(f"ix_{table}_warehouse_id", table_name=table)
        op.drop_constraint(f"fk_{table}_warehouse_id", table, type_="foreignkey")
        op.drop_column(table, "warehouse_id")
    op.drop_index("ix_warehouses_branch_id", table_name="warehouses")
    op.drop_table("warehouses")
