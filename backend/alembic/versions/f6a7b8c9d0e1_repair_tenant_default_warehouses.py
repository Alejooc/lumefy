"""repair default warehouses for tenants created after warehouse rollout

Revision ID: f6a7b8c9d0e1
Revises: f5a6b7c8d9e0
"""

from alembic import op


revision = "f6a7b8c9d0e1"
down_revision = "f5a6b7c8d9e0"
branch_labels = depends_on = None


def upgrade() -> None:
    # The original warehouse migration backfilled branches that existed at the
    # time.  Tenant onboarding previously skipped this step for companies made
    # afterwards, leaving their operational modules without a stock source.
    op.execute("""
        INSERT INTO warehouses (
            id, branch_id, name, code, is_default, allows_ecommerce,
            company_id, created_at, updated_at, is_active
        )
        SELECT
            gen_random_uuid(), b.id, 'Bodega principal', 'PRINCIPAL', true, true,
            b.company_id, now(), now(), true
        FROM branches b
        WHERE NOT EXISTS (
            SELECT 1
            FROM warehouses w
            WHERE w.branch_id = b.id AND w.is_default = true
        )
    """)


def downgrade() -> None:
    # Do not delete business data created by the repair.
    pass
