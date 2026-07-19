"""add invoicing documents

Revision ID: f1a9c0d4e7b2
Revises: cf4e3b2a9d6f
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f1a9c0d4e7b2"
down_revision: Union[str, None] = "cf4e3b2a9d6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    invoice_type = postgresql.ENUM("SALE", "PURCHASE", name="invoicetype", create_type=False)
    invoice_status = postgresql.ENUM("DRAFT", "POSTED", "PARTIALLY_PAID", "PAID", "CANCELLED", name="invoicestatus", create_type=False)
    invoice_type.create(op.get_bind(), checkfirst=True)
    invoice_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "invoices",
        sa.Column("number", sa.String(), nullable=False),
        sa.Column("type", invoice_type, nullable=False),
        sa.Column("status", invoice_status, nullable=False),
        sa.Column("branch_id", sa.UUID(), nullable=True),
        sa.Column("client_id", sa.UUID(), nullable=True),
        sa.Column("supplier_id", sa.UUID(), nullable=True),
        sa.Column("sale_id", sa.UUID(), nullable=True),
        sa.Column("purchase_id", sa.UUID(), nullable=True),
        sa.Column("issue_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subtotal", sa.Float(), nullable=False),
        sa.Column("tax", sa.Float(), nullable=False),
        sa.Column("total", sa.Float(), nullable=False),
        sa.Column("amount_paid", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"]),
        sa.ForeignKeyConstraint(["purchase_id"], ["purchase_orders.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "number", name="uq_invoices_company_number"),
    )
    op.create_index(op.f("ix_invoices_number"), "invoices", ["number"], unique=False)
    op.create_index(op.f("ix_invoices_type"), "invoices", ["type"], unique=False)
    op.create_index(op.f("ix_invoices_status"), "invoices", ["status"], unique=False)
    op.create_index(op.f("ix_invoices_sale_id"), "invoices", ["sale_id"], unique=False)
    op.create_index(op.f("ix_invoices_purchase_id"), "invoices", ["purchase_id"], unique=False)

    op.create_table(
        "invoice_items",
        sa.Column("invoice_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=True),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("tax_rate", sa.Float(), nullable=False),
        sa.Column("subtotal", sa.Float(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoice_items_invoice_id"), "invoice_items", ["invoice_id"], unique=False)

    op.create_table(
        "invoice_payments",
        sa.Column("invoice_id", sa.UUID(), nullable=False),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoice_payments_invoice_id"), "invoice_payments", ["invoice_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_invoice_payments_invoice_id"), table_name="invoice_payments")
    op.drop_table("invoice_payments")
    op.drop_index(op.f("ix_invoice_items_invoice_id"), table_name="invoice_items")
    op.drop_table("invoice_items")
    op.drop_index(op.f("ix_invoices_purchase_id"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_sale_id"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_status"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_type"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_number"), table_name="invoices")
    op.drop_table("invoices")
    sa.Enum(name="invoicestatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="invoicetype").drop(op.get_bind(), checkfirst=True)
