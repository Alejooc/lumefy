"""add encrypted app secrets and checkout tracking consent.

Revision ID: fr6a7b8c9d0e
Revises: fq5e6f7a8b9c
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fr6a7b8c9d0e"
down_revision: Union[str, None] = "fq5e6f7a8b9c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "company_app_installs",
        sa.Column("private_settings", sa.JSON(), nullable=True),
    )
    op.add_column(
        "storefront_orders",
        sa.Column("tracking_consent_analytics", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "storefront_orders",
        sa.Column("tracking_consent_marketing", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.alter_column("storefront_orders", "tracking_consent_analytics", server_default=None)
    op.alter_column("storefront_orders", "tracking_consent_marketing", server_default=None)


def downgrade() -> None:
    op.drop_column("storefront_orders", "tracking_consent_marketing")
    op.drop_column("storefront_orders", "tracking_consent_analytics")
    op.drop_column("company_app_installs", "private_settings")
