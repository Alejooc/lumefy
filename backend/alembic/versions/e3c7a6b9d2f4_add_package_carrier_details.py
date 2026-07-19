"""add package carrier details

Revision ID: e3c7a6b9d2f4
Revises: d4f8b2c6e1a5
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3c7a6b9d2f4"
down_revision: Union[str, None] = "d4f8b2c6e1a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sale_packages", sa.Column("carrier", sa.String(), nullable=True))
    op.add_column("sale_packages", sa.Column("service_level", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("sale_packages", "service_level")
    op.drop_column("sale_packages", "carrier")
