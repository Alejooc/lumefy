"""link products to homologated suppliers

Revision ID: a2b3c4d5e6f7
Revises: ff5a6b7c8d9e
"""

from alembic import op
import sqlalchemy as sa


revision = "a2b3c4d5e6f7"
down_revision = "ff5a6b7c8d9e"
branch_labels = depends_on = None


def upgrade() -> None:
    op.add_column("suppliers", sa.Column("external_id", sa.String(), nullable=True))
    op.create_index("ix_suppliers_external_id", "suppliers", ["external_id"], unique=False)
    op.create_index(
        "uq_suppliers_company_external_id",
        "suppliers",
        ["company_id", "external_id"],
        unique=True,
    )

    op.add_column("products", sa.Column("supplier_id", sa.UUID(), nullable=True))
    op.create_index("ix_products_supplier_id", "products", ["supplier_id"], unique=False)
    op.create_foreign_key(
        "fk_products_supplier_id_suppliers",
        "products",
        "suppliers",
        ["supplier_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_products_supplier_id_suppliers", "products", type_="foreignkey")
    op.drop_index("ix_products_supplier_id", table_name="products")
    op.drop_column("products", "supplier_id")
    op.drop_index("uq_suppliers_company_external_id", table_name="suppliers")
    op.drop_index("ix_suppliers_external_id", table_name="suppliers")
    op.drop_column("suppliers", "external_id")
