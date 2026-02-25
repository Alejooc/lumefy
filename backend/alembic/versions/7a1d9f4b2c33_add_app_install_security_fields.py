"""add_app_install_security_fields

Revision ID: 7a1d9f4b2c33
Revises: 6f4d2f8c9b10
Create Date: 2026-02-25 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7a1d9f4b2c33"
down_revision: Union[str, None] = "6f4d2f8c9b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("company_app_installs", sa.Column("api_key_prefix", sa.String(), nullable=True))
    op.add_column("company_app_installs", sa.Column("api_key_hash", sa.String(), nullable=True))
    op.add_column("company_app_installs", sa.Column("webhook_secret", sa.String(), nullable=True))
    op.add_column("company_app_installs", sa.Column("webhook_url", sa.String(), nullable=True))
    op.add_column(
        "company_app_installs",
        sa.Column("billing_status", sa.String(), nullable=False, server_default="active"),
    )


def downgrade() -> None:
    op.drop_column("company_app_installs", "billing_status")
    op.drop_column("company_app_installs", "webhook_url")
    op.drop_column("company_app_installs", "webhook_secret")
    op.drop_column("company_app_installs", "api_key_hash")
    op.drop_column("company_app_installs", "api_key_prefix")
