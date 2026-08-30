"""add pricing-list rounding modes.

Revision ID: fv0a1b2c3d4e
Revises: fu9e0f1a2b3c
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fv0a1b2c3d4e"
down_revision: Union[str, None] = "fu9e0f1a2b3c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "price_lists",
        sa.Column("rounding_mode", sa.String(length=20), nullable=False, server_default="NEAREST"),
    )
    op.add_column(
        "pricelist_source_rules",
        sa.Column("rounding_mode", sa.String(length=20), nullable=False, server_default="NEAREST"),
    )


def downgrade() -> None:
    op.drop_column("pricelist_source_rules", "rounding_mode")
    op.drop_column("price_lists", "rounding_mode")
