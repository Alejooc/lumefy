"""add inventory average cost

Revision ID: b9d3e5f7a2c4
Revises: e2b7f4a9c1d6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b9d3e5f7a2c4"
down_revision: Union[str, None] = "e2b7f4a9c1d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("inventory", sa.Column("average_cost", sa.Float(), nullable=False, server_default="0"))
    op.add_column("inventory_movements", sa.Column("unit_cost", sa.Float(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("inventory_movements", "unit_cost")
    op.drop_column("inventory", "average_cost")
