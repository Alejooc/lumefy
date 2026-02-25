"""add_shopify_like_marketplace_fields

Revision ID: 6f4d2f8c9b10
Revises: c9076a6d1ddc
Create Date: 2026-02-25 10:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6f4d2f8c9b10"
down_revision: Union[str, None] = "c9076a6d1ddc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("app_definitions", sa.Column("requested_scopes", sa.JSON(), nullable=True))
    op.add_column("app_definitions", sa.Column("capabilities", sa.JSON(), nullable=True))
    op.add_column("app_definitions", sa.Column("setup_url", sa.String(), nullable=True))
    op.add_column("app_definitions", sa.Column("docs_url", sa.String(), nullable=True))
    op.add_column("app_definitions", sa.Column("support_url", sa.String(), nullable=True))
    op.add_column("app_definitions", sa.Column("pricing_model", sa.String(), nullable=False, server_default="free"))
    op.add_column("app_definitions", sa.Column("monthly_price", sa.Float(), nullable=True, server_default="0"))
    op.add_column("app_definitions", sa.Column("is_listed", sa.Boolean(), nullable=False, server_default=sa.text("true")))

    op.add_column(
        "company_app_installs",
        sa.Column("installed_version", sa.String(), nullable=False, server_default="1.0.0"),
    )
    op.add_column("company_app_installs", sa.Column("granted_scopes", sa.JSON(), nullable=True))

    op.create_table(
        "app_install_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("app_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("triggered_by_user_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["app_id"], ["app_definitions.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_app_install_events_company_id"), "app_install_events", ["company_id"], unique=False)
    op.create_index(op.f("ix_app_install_events_app_id"), "app_install_events", ["app_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_app_install_events_app_id"), table_name="app_install_events")
    op.drop_index(op.f("ix_app_install_events_company_id"), table_name="app_install_events")
    op.drop_table("app_install_events")

    op.drop_column("company_app_installs", "granted_scopes")
    op.drop_column("company_app_installs", "installed_version")

    op.drop_column("app_definitions", "is_listed")
    op.drop_column("app_definitions", "monthly_price")
    op.drop_column("app_definitions", "pricing_model")
    op.drop_column("app_definitions", "support_url")
    op.drop_column("app_definitions", "docs_url")
    op.drop_column("app_definitions", "setup_url")
    op.drop_column("app_definitions", "capabilities")
    op.drop_column("app_definitions", "requested_scopes")
