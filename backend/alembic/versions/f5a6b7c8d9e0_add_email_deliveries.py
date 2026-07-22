"""add durable email deliveries

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f5a6b7c8d9e0"
down_revision = "e4f5a6b7c8d9"
branch_labels = depends_on = None

def upgrade():
    op.create_table("email_deliveries", sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outbox_events.id"), nullable=False), sa.Column("recipient", sa.String(), nullable=False), sa.Column("subject", sa.String(), nullable=False), sa.Column("html_content", sa.Text(), nullable=False), sa.Column("status", sa.String(), nullable=False), sa.Column("attempts", sa.Integer(), nullable=False), sa.Column("available_at", sa.DateTime(), nullable=False), sa.Column("sent_at", sa.DateTime(), nullable=True), sa.Column("last_error", sa.Text(), nullable=True), sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False), sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True), sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True), sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=True), sa.UniqueConstraint("event_id", name="uq_email_delivery_event"))
    op.create_index("ix_email_deliveries_status", "email_deliveries", ["status"])

def downgrade(): op.drop_table("email_deliveries")
