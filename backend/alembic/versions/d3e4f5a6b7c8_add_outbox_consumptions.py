"""add outbox consumer idempotency receipts

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "outbox_consumptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outbox_events.id"), nullable=False),
        sa.Column("consumer", sa.String(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("event_id", "consumer", name="uq_outbox_consumption_event_consumer"),
    )
    op.create_index("ix_outbox_consumptions_event_id", "outbox_consumptions", ["event_id"])
    op.create_index("ix_outbox_consumptions_consumer", "outbox_consumptions", ["consumer"])

def downgrade() -> None:
    op.drop_table("outbox_consumptions")
