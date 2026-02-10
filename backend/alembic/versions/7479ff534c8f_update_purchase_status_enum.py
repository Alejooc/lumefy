"""update_purchase_status_enum

Revision ID: 7479ff534c8f
Revises: ee06c75add9f
Create Date: 2026-02-10 11:07:56.609108

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7479ff534c8f'
down_revision: Union[str, None] = 'ee06c75add9f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot be executed inside a transaction block
    connection = op.get_bind()
    connection.execute(sa.text("COMMIT"))
    connection.execute(sa.text("ALTER TYPE purchasestatus ADD VALUE 'VALIDATION'"))
    connection.execute(sa.text("BEGIN"))


def downgrade() -> None:
    pass
