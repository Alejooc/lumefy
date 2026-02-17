"""add_app_marketplace_tables

Revision ID: c1f8b0fce2a1
Revises: 891596236182
Create Date: 2026-02-16 19:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1f8b0fce2a1"
down_revision: Union[str, None] = "891596236182"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_definitions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("icon", sa.String(), nullable=True),
        sa.Column("config_schema", sa.JSON(), nullable=True),
        sa.Column("default_config", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_app_definitions_slug"), "app_definitions", ["slug"], unique=True)

    op.create_table(
        "company_app_installs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("app_id", sa.UUID(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=True),
        sa.Column("settings", sa.JSON(), nullable=True),
        sa.Column("installed_by_user_id", sa.UUID(), nullable=True),
        sa.Column("installed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["app_id"], ["app_definitions.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["installed_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "app_id", name="uq_company_app_install"),
    )
    op.create_index(op.f("ix_company_app_installs_app_id"), "company_app_installs", ["app_id"], unique=False)
    op.create_index(op.f("ix_company_app_installs_company_id"), "company_app_installs", ["company_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_company_app_installs_company_id"), table_name="company_app_installs")
    op.drop_index(op.f("ix_company_app_installs_app_id"), table_name="company_app_installs")
    op.drop_table("company_app_installs")
    op.drop_index(op.f("ix_app_definitions_slug"), table_name="app_definitions")
    op.drop_table("app_definitions")
