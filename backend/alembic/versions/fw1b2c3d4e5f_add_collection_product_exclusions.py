"""add automated collection product exclusions.

Revision ID: fw1b2c3d4e5f
Revises: fv0a1b2c3d4e
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fw1b2c3d4e5f"
down_revision: Union[str, None] = "fv0a1b2c3d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "store_collection_products",
        sa.Column("is_excluded", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("store_collection_products", "is_excluded")
