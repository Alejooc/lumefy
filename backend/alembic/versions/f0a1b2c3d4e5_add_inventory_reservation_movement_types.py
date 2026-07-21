"""add inventory reservation movement types

Revision ID: f0a1b2c3d4e5
Revises: e9a7d5c3b1f0
"""
from typing import Sequence, Union

from alembic import op


revision: str = "f0a1b2c3d4e5"
down_revision: Union[str, None] = "e9a7d5c3b1f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL enum values must be committed before application code can use
    # them in a later transaction.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE movementtype ADD VALUE IF NOT EXISTS 'RESERVE'")
        op.execute("ALTER TYPE movementtype ADD VALUE IF NOT EXISTS 'RELEASE'")


def downgrade() -> None:
    # PostgreSQL does not safely remove enum values in-place. Keeping them is
    # intentional: historic audit rows must remain readable.
    pass
