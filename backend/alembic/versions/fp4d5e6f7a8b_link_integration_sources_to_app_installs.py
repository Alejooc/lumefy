"""link integration connections to tenant app installations.

Revision ID: fp4d5e6f7a8b
Revises: fo3c4d5e6f7a
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fp4d5e6f7a8b"
down_revision: Union[str, None] = "fo3c4d5e6f7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "integration_sources",
        sa.Column("app_install_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        "ix_integration_sources_app_install_id",
        "integration_sources",
        ["app_install_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_integration_sources_app_install_id",
        "integration_sources",
        "company_app_installs",
        ["app_install_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_integration_sources_app_install_id",
        "integration_sources",
        type_="foreignkey",
    )
    op.drop_index("ix_integration_sources_app_install_id", table_name="integration_sources")
    op.drop_column("integration_sources", "app_install_id")
