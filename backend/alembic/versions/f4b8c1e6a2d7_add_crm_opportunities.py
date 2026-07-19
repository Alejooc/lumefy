"""add crm opportunities

Revision ID: f4b8c1e6a2d7
Revises: e3c7a6b9d2f4
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4b8c1e6a2d7"
down_revision: Union[str, None] = "e3c7a6b9d2f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "opportunities",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("stage", sa.Enum("NEW", "QUALIFIED", "PROPOSAL", "WON", "LOST", name="opportunitystage"), nullable=False),
        sa.Column("expected_revenue", sa.Float(), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("expected_close_date", sa.Date(), nullable=True),
        sa.Column("contact_name", sa.String(), nullable=True),
        sa.Column("contact_email", sa.String(), nullable=True),
        sa.Column("contact_phone", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("lost_reason", sa.String(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_opportunities_client_id"), "opportunities", ["client_id"], unique=False)
    op.create_index(op.f("ix_opportunities_owner_id"), "opportunities", ["owner_id"], unique=False)
    op.create_index(op.f("ix_opportunities_stage"), "opportunities", ["stage"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_opportunities_stage"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_owner_id"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_client_id"), table_name="opportunities")
    op.drop_table("opportunities")
    op.execute("DROP TYPE IF EXISTS opportunitystage")
