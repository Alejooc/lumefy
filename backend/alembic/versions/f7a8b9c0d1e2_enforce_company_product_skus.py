"""enforce active product SKU uniqueness per company

Revision ID: f7a8b9c0d1e2
Revises: f6a7b8c9d0e1
"""

from alembic import op


revision = "f7a8b9c0d1e2"
down_revision = "f6a7b8c9d0e1"
branch_labels = depends_on = None


def upgrade() -> None:
    # Preserve all legacy rows while making their identifiers unique. The
    # first product keeps the original SKU; later duplicates receive a
    # deterministic suffix based on their UUID and can be edited normally.
    op.execute("""
        DO $$
        DECLARE duplicate_row RECORD;
        BEGIN
            FOR duplicate_row IN
                SELECT id, sku,
                       row_number() OVER (
                           PARTITION BY company_id, lower(btrim(sku))
                           ORDER BY created_at ASC, id ASC
                       ) AS duplicate_number
                FROM products
                WHERE sku IS NOT NULL AND btrim(sku) <> '' AND is_active = true
            LOOP
                IF duplicate_row.duplicate_number > 1 THEN
                    UPDATE products
                    SET sku = btrim(duplicate_row.sku) || '-LEGACY-' || replace(duplicate_row.id::text, '-', '')
                    WHERE id = duplicate_row.id;
                END IF;
            END LOOP;
        END $$;
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_products_company_active_sku
        ON products (company_id, lower(btrim(sku)))
        WHERE is_active = true AND sku IS NOT NULL AND btrim(sku) <> ''
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_products_company_active_sku")
