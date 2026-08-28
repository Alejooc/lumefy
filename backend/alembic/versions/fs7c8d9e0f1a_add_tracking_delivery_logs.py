"""add server-side tracking delivery logs.

Revision ID: fs7c8d9e0f1a
Revises: fr6a7b8c9d0e
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "fs7c8d9e0f1a"
down_revision: Union[str, None] = "fr6a7b8c9d0e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_tracking_deliveries",
        sa.Column("app_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("install_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outbox_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("event_name", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["app_id"], ["app_definitions.id"]),
        sa.ForeignKeyConstraint(["install_id"], ["company_app_installs.id"]),
        sa.ForeignKeyConstraint(["outbox_event_id"], ["outbox_events.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("outbox_event_id", "app_id", name="uq_app_tracking_delivery_event_app"),
    )
    op.create_index(
        op.f("ix_app_tracking_deliveries_app_id"),
        "app_tracking_deliveries",
        ["app_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_app_tracking_deliveries_install_id"),
        "app_tracking_deliveries",
        ["install_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_app_tracking_deliveries_outbox_event_id"),
        "app_tracking_deliveries",
        ["outbox_event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_app_tracking_deliveries_event_id"),
        "app_tracking_deliveries",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_app_tracking_deliveries_status"),
        "app_tracking_deliveries",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_app_tracking_deliveries_status"), table_name="app_tracking_deliveries")
    op.drop_index(op.f("ix_app_tracking_deliveries_event_id"), table_name="app_tracking_deliveries")
    op.drop_index(op.f("ix_app_tracking_deliveries_outbox_event_id"), table_name="app_tracking_deliveries")
    op.drop_index(op.f("ix_app_tracking_deliveries_install_id"), table_name="app_tracking_deliveries")
    op.drop_index(op.f("ix_app_tracking_deliveries_app_id"), table_name="app_tracking_deliveries")
    op.drop_table("app_tracking_deliveries")
