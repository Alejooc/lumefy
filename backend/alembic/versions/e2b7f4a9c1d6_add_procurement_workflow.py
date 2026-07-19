"""add procurement workflow

Revision ID: e2b7f4a9c1d6
Revises: f1a9c0d4e7b2
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e2b7f4a9c1d6"
down_revision: Union[str, None] = "f1a9c0d4e7b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    request_status = postgresql.ENUM("DRAFT", "SUBMITTED", "APPROVED", "CONVERTED", "CANCELLED", name="purchaserequeststatus", create_type=False)
    quote_status = postgresql.ENUM("DRAFT", "SUBMITTED", "ACCEPTED", "REJECTED", name="supplierquotestatus", create_type=False)
    request_status.create(op.get_bind(), checkfirst=True)
    quote_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "purchase_requests",
        sa.Column("branch_id", sa.UUID(), nullable=False),
        sa.Column("requested_by_id", sa.UUID(), nullable=False),
        sa.Column("purchase_order_id", sa.UUID(), nullable=True),
        sa.Column("status", request_status, nullable=False),
        sa.Column("priority", sa.String(), nullable=False),
        sa.Column("requested_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_purchase_requests_status"), "purchase_requests", ["status"], unique=False)
    op.create_table(
        "purchase_request_items",
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["request_id"], ["purchase_requests.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_purchase_request_items_request_id"), "purchase_request_items", ["request_id"], unique=False)
    op.create_table(
        "supplier_quotes",
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("supplier_id", sa.UUID(), nullable=False),
        sa.Column("status", quote_status, nullable=False),
        sa.Column("reference_number", sa.String(), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_amount", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["request_id"], ["purchase_requests.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_supplier_quotes_request_id"), "supplier_quotes", ["request_id"], unique=False)
    op.create_index(op.f("ix_supplier_quotes_status"), "supplier_quotes", ["status"], unique=False)
    op.create_table(
        "supplier_quote_items",
        sa.Column("quote_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit_cost", sa.Float(), nullable=False),
        sa.Column("subtotal", sa.Float(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["quote_id"], ["supplier_quotes.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_supplier_quote_items_quote_id"), "supplier_quote_items", ["quote_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_supplier_quote_items_quote_id"), table_name="supplier_quote_items")
    op.drop_table("supplier_quote_items")
    op.drop_index(op.f("ix_supplier_quotes_status"), table_name="supplier_quotes")
    op.drop_index(op.f("ix_supplier_quotes_request_id"), table_name="supplier_quotes")
    op.drop_table("supplier_quotes")
    op.drop_index(op.f("ix_purchase_request_items_request_id"), table_name="purchase_request_items")
    op.drop_table("purchase_request_items")
    op.drop_index(op.f("ix_purchase_requests_status"), table_name="purchase_requests")
    op.drop_table("purchase_requests")
    sa.Enum(name="supplierquotestatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="purchaserequeststatus").drop(op.get_bind(), checkfirst=True)
