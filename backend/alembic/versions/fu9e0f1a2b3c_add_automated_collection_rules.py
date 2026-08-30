"""add automated storefront collection rules.

Revision ID: fu9e0f1a2b3c
Revises: ft8d9e0f1a2b
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "fu9e0f1a2b3c"
down_revision: Union[str, None] = "ft8d9e0f1a2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "store_collections",
        sa.Column("collection_mode", sa.String(length=16), nullable=False, server_default="manual"),
    )
    op.add_column(
        "store_collections",
        sa.Column("rule_match", sa.String(length=8), nullable=False, server_default="all"),
    )
    op.create_table(
        "store_collection_rules",
        sa.Column("collection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field", sa.String(length=32), nullable=False),
        sa.Column("operator", sa.String(length=32), nullable=False),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["collection_id"], ["store_collections.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("collection_id", "position", name="uq_store_collection_rule_position"),
    )
    op.create_index(
        op.f("ix_store_collection_rules_collection_id"),
        "store_collection_rules",
        ["collection_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_store_collection_rules_company_id"),
        "store_collection_rules",
        ["company_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_store_collection_rules_company_id"), table_name="store_collection_rules")
    op.drop_index(op.f("ix_store_collection_rules_collection_id"), table_name="store_collection_rules")
    op.drop_table("store_collection_rules")
    op.drop_column("store_collections", "rule_match")
    op.drop_column("store_collections", "collection_mode")
