"""add integration sync queue and inventory schedule

Revision ID: fc2d3e4f5a6b
Revises: fb1c2d3e4f5a
"""

from alembic import op
import sqlalchemy as sa


revision = "fc2d3e4f5a6b"
down_revision = "fb1c2d3e4f5a"
branch_labels = depends_on = None


def upgrade() -> None:
    op.add_column("integration_sources", sa.Column("last_catalog_synced_at", sa.DateTime(), nullable=True))
    op.add_column("integration_sources", sa.Column("last_inventory_synced_at", sa.DateTime(), nullable=True))
    op.add_column(
        "integration_sources",
        sa.Column("inventory_sync_mode", sa.String(length=20), nullable=False, server_default="MANUAL"),
    )
    op.add_column("integration_sources", sa.Column("inventory_sync_interval_minutes", sa.Integer(), nullable=True))
    op.add_column("integration_sources", sa.Column("next_inventory_sync_at", sa.DateTime(), nullable=True))
    op.create_index(
        "ix_integration_sources_next_inventory_sync_at",
        "integration_sources",
        ["next_inventory_sync_at"],
    )

    op.add_column(
        "integration_sync_runs",
        sa.Column("sync_type", sa.String(length=20), nullable=False, server_default="FULL"),
    )
    op.add_column(
        "integration_sync_runs",
        sa.Column("trigger_type", sa.String(length=20), nullable=False, server_default="MANUAL"),
    )
    op.add_column(
        "integration_sync_runs",
        sa.Column("queued_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.alter_column("integration_sync_runs", "started_at", existing_type=sa.DateTime(), nullable=True)
    op.execute(
        """
        UPDATE integration_sync_runs
        SET
            status = 'FAILED',
            finished_at = COALESCE(finished_at, now()),
            error_message = COALESCE(error_message, 'Ejecución anterior interrumpida durante la actualización.')
        WHERE status = 'RUNNING'
        """
    )
    op.create_index(
        "uq_integration_sync_runs_active_type",
        "integration_sync_runs",
        ["source_id", "sync_type"],
        unique=True,
        postgresql_where=sa.text("status IN ('QUEUED', 'RUNNING')"),
    )
    op.create_index(
        "uq_integration_sync_runs_running_source",
        "integration_sync_runs",
        ["source_id"],
        unique=True,
        postgresql_where=sa.text("status = 'RUNNING'"),
    )

    # Inventory historically had no uniqueness boundary. Keep the most recently
    # updated row for each stock identity before enforcing the invariant.
    op.execute(
        """
        DELETE FROM inventory AS duplicate
        USING (
            SELECT id
            FROM (
                SELECT
                    id,
                    row_number() OVER (
                        PARTITION BY company_id, product_id, branch_id, warehouse_id, variant_id
                        ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST, id DESC
                    ) AS row_number
                FROM inventory
            ) AS ranked
            WHERE ranked.row_number > 1
        ) AS discarded
        WHERE duplicate.id = discarded.id
        """
    )
    op.create_index(
        "uq_inventory_stock_identity",
        "inventory",
        ["company_id", "product_id", "branch_id", "warehouse_id", "variant_id"],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )


def downgrade() -> None:
    op.drop_index("uq_inventory_stock_identity", table_name="inventory")
    op.drop_index("uq_integration_sync_runs_running_source", table_name="integration_sync_runs")
    op.drop_index("uq_integration_sync_runs_active_type", table_name="integration_sync_runs")
    op.execute(
        """
        UPDATE integration_sync_runs
        SET started_at = COALESCE(started_at, queued_at, created_at, now())
        WHERE started_at IS NULL
        """
    )
    op.alter_column("integration_sync_runs", "started_at", existing_type=sa.DateTime(), nullable=False)
    op.drop_column("integration_sync_runs", "queued_at")
    op.drop_column("integration_sync_runs", "trigger_type")
    op.drop_column("integration_sync_runs", "sync_type")

    op.drop_index("ix_integration_sources_next_inventory_sync_at", table_name="integration_sources")
    op.drop_column("integration_sources", "next_inventory_sync_at")
    op.drop_column("integration_sources", "inventory_sync_interval_minutes")
    op.drop_column("integration_sources", "inventory_sync_mode")
    op.drop_column("integration_sources", "last_inventory_synced_at")
    op.drop_column("integration_sources", "last_catalog_synced_at")
