"""merge gateway and integration migration branches

Revision ID: fa0b1c2d3e4f
Revises: c3d4e5f6a7b8, f9a0b1c2d3e4
"""

from typing import Sequence


revision: str = "fa0b1c2d3e4f"
down_revision: tuple[str, str] = ("c3d4e5f6a7b8", "f9a0b1c2d3e4")
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
