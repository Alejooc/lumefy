"""add inventory reservations

Revision ID: d4f8b2c6e1a5
Revises: c8e4a1f6d9b3
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4f8b2c6e1a5"
down_revision: Union[str, None] = "c8e4a1f6d9b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("inventory", sa.Column("reserved_quantity", sa.Float(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("inventory", "reserved_quantity")
