"""add fulfillment tasks driven by inventory events

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "fulfillment_tasks",
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sales.id"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id"), nullable=True),
        sa.Column("task_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=True),
        sa.UniqueConstraint("sale_id", "task_type", name="uq_fulfillment_task_sale_type"),
    )
    op.create_index("ix_fulfillment_tasks_sale_id", "fulfillment_tasks", ["sale_id"])
    op.create_index("ix_fulfillment_tasks_warehouse_id", "fulfillment_tasks", ["warehouse_id"])
    op.create_index("ix_fulfillment_tasks_status", "fulfillment_tasks", ["status"])

def downgrade() -> None:
    op.drop_table("fulfillment_tasks")
