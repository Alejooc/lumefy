"""add company subscription status

Revision ID: ad9f5b8e3c17
Revises: 7e2f4c9a1d11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ad9f5b8e3c17"
down_revision: Union[str, None] = "7e2f4c9a1d11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("subscription_status", sa.String(), nullable=False, server_default="ACTIVE"),
    )


def downgrade() -> None:
    op.drop_column("companies", "subscription_status")
