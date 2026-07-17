"""retire demo hello app

Revision ID: cf4e3b2a9d6f
Revises: ad9f5b8e3c17
"""
from typing import Sequence, Union

from alembic import op


revision: str = "cf4e3b2a9d6f"
down_revision: Union[str, None] = "ad9f5b8e3c17"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE app_definitions SET is_active = false, is_listed = false WHERE slug = 'demo-hello'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE app_definitions SET is_active = true, is_listed = true WHERE slug = 'demo-hello'"
    )
