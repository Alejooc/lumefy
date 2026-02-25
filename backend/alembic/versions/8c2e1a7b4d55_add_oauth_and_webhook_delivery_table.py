"""add_oauth_and_webhook_delivery_table

Revision ID: 8c2e1a7b4d55
Revises: 7a1d9f4b2c33
Create Date: 2026-02-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8c2e1a7b4d55"
down_revision: Union[str, None] = "7a1d9f4b2c33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("company_app_installs", sa.Column("oauth_client_id", sa.String(), nullable=True))
    op.add_column("company_app_installs", sa.Column("oauth_client_secret_hash", sa.String(), nullable=True))

    op.create_table(
        "app_webhook_deliveries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("app_id", sa.UUID(), nullable=False),
        sa.Column("install_id", sa.UUID(), nullable=False),
        sa.Column("event_name", sa.String(), nullable=False),
        sa.Column("endpoint", sa.String(), nullable=True),
        sa.Column("request_payload", sa.JSON(), nullable=True),
        sa.Column("signature", sa.String(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["app_id"], ["app_definitions.id"]),
        sa.ForeignKeyConstraint(["install_id"], ["company_app_installs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_app_webhook_deliveries_company_id"), "app_webhook_deliveries", ["company_id"], unique=False)
    op.create_index(op.f("ix_app_webhook_deliveries_app_id"), "app_webhook_deliveries", ["app_id"], unique=False)
    op.create_index(op.f("ix_app_webhook_deliveries_install_id"), "app_webhook_deliveries", ["install_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_app_webhook_deliveries_install_id"), table_name="app_webhook_deliveries")
    op.drop_index(op.f("ix_app_webhook_deliveries_app_id"), table_name="app_webhook_deliveries")
    op.drop_index(op.f("ix_app_webhook_deliveries_company_id"), table_name="app_webhook_deliveries")
    op.drop_table("app_webhook_deliveries")

    op.drop_column("company_app_installs", "oauth_client_secret_hash")
    op.drop_column("company_app_installs", "oauth_client_id")
