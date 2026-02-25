"""merge_marketplace_and_pos_heads

Revision ID: c4f8a2b7d3e1
Revises: 8c2e1a7b4d55, b19d7c4a91f0
Create Date: 2026-02-25 00:30:00.000000

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "c4f8a2b7d3e1"
down_revision: Union[str, Sequence[str], None] = ("8c2e1a7b4d55", "b19d7c4a91f0")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

