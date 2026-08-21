"""add idempotent integration webhook events

Revision ID: fi8a9b0c1d2e
Revises: fh7b8c9d0e1f
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "fi8a9b0c1d2e"
down_revision = "fh7b8c9d0e1f"
branch_labels = depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_webhook_events",
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sync_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_key", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False, server_default="unknown"),
        sa.Column("sync_type", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="QUEUED"),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["integration_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sync_run_id"], ["integration_sync_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "event_key", name="uq_integration_webhook_source_event"),
    )
    op.create_index(
        "ix_integration_webhook_events_source_id",
        "integration_webhook_events",
        ["source_id"],
    )
    op.create_index(
        "ix_integration_webhook_events_sync_run_id",
        "integration_webhook_events",
        ["sync_run_id"],
    )
    op.create_index(
        "ix_integration_webhook_events_received_at",
        "integration_webhook_events",
        ["received_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_integration_webhook_events_received_at", table_name="integration_webhook_events")
    op.drop_index("ix_integration_webhook_events_sync_run_id", table_name="integration_webhook_events")
    op.drop_index("ix_integration_webhook_events_source_id", table_name="integration_webhook_events")
    op.drop_table("integration_webhook_events")
