"""separate storefront customer accounts from internal users

Revision ID: f8b9c0d1e2f3
Revises: f7a8b9c0d1e2
"""

from alembic import op
import sqlalchemy as sa


revision = "f8b9c0d1e2f3"
down_revision = "f7a8b9c0d1e2"
branch_labels = depends_on = None


def upgrade() -> None:
    op.create_table(
        "storefront_customer_accounts",
        sa.Column("storefront_id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "storefront_id",
            "email",
            name="uq_storefront_customer_account_storefront_email",
        ),
    )
    op.create_index(
        "ix_storefront_customer_accounts_storefront_id",
        "storefront_customer_accounts",
        ["storefront_id"],
    )
    op.create_index(
        "ix_storefront_customer_accounts_client_id",
        "storefront_customer_accounts",
        ["client_id"],
    )
    op.create_index(
        "ix_storefront_customer_accounts_email",
        "storefront_customer_accounts",
        ["email"],
    )

    # Public registrations were previously stored as users without a role.
    # Preserve those credentials in the new account boundary and create the
    # CRM client that the storefront checkout already expects.
    op.execute(
        """
        INSERT INTO clients (
            id, name, email, status, notes, created_at, updated_at,
            is_active, company_id
        )
        SELECT
            gen_random_uuid(),
            COALESCE(NULLIF(btrim(u.full_name), ''), u.email),
            lower(u.email),
            'active',
            'Migrated from legacy storefront account',
            u.created_at,
            u.updated_at,
            u.is_active,
            u.company_id
        FROM users u
        WHERE u.role_id IS NULL
          AND u.is_superuser = false
          AND u.company_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM clients c
              WHERE c.company_id = u.company_id
                AND lower(c.email) = lower(u.email)
          )
        """
    )
    op.execute(
        """
        INSERT INTO storefront_customer_accounts (
            id, storefront_id, client_id, email, hashed_password, full_name,
            created_at, updated_at, is_active, company_id
        )
        SELECT
            gen_random_uuid(),
            s.id,
            c.id,
            lower(u.email),
            u.hashed_password,
            u.full_name,
            u.created_at,
            u.updated_at,
            u.is_active,
            s.company_id
        FROM users u
        JOIN storefronts s ON s.company_id = u.company_id AND s.is_active = true
        LEFT JOIN clients c
          ON c.company_id = u.company_id
         AND lower(c.email) = lower(u.email)
        WHERE u.role_id IS NULL
          AND u.is_superuser = false
          AND u.company_id IS NOT NULL
        ON CONFLICT (storefront_id, email) DO NOTHING
        """
    )

    op.add_column(
        "storefront_orders",
        sa.Column("customer_account_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        "ix_storefront_orders_customer_account_id",
        "storefront_orders",
        ["customer_account_id"],
    )
    op.execute(
        """
        UPDATE storefront_orders so
        SET customer_account_id = account.id
        FROM storefront_customer_accounts account
        JOIN users legacy_user
          ON lower(legacy_user.email) = account.email
         AND legacy_user.company_id = account.company_id
        WHERE so.customer_user_id = legacy_user.id
          AND so.storefront_id = account.storefront_id
        """
    )

    op.execute(
        "ALTER TABLE storefront_orders DROP CONSTRAINT IF EXISTS storefront_orders_customer_user_id_fkey"
    )
    op.drop_index("ix_storefront_orders_customer_user_id", table_name="storefront_orders")
    op.drop_column("storefront_orders", "customer_user_id")
    op.create_foreign_key(
        "fk_storefront_orders_customer_account_id",
        "storefront_orders",
        "storefront_customer_accounts",
        ["customer_account_id"],
        ["id"],
    )


def downgrade() -> None:
    op.add_column(
        "storefront_orders",
        sa.Column("customer_user_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        "ix_storefront_orders_customer_user_id",
        "storefront_orders",
        ["customer_user_id"],
    )
    op.execute(
        """
        UPDATE storefront_orders so
        SET customer_user_id = legacy_user.id
        FROM storefront_customer_accounts account
        JOIN users legacy_user
          ON lower(legacy_user.email) = account.email
         AND legacy_user.company_id = account.company_id
        WHERE so.customer_account_id = account.id
        """
    )
    op.create_foreign_key(
        "fk_storefront_orders_customer_user_id",
        "storefront_orders",
        "users",
        ["customer_user_id"],
        ["id"],
    )
    op.drop_constraint(
        "fk_storefront_orders_customer_account_id",
        "storefront_orders",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_storefront_orders_customer_account_id",
        table_name="storefront_orders",
    )
    op.drop_column("storefront_orders", "customer_account_id")
    op.drop_index(
        "ix_storefront_customer_accounts_email",
        table_name="storefront_customer_accounts",
    )
    op.drop_index(
        "ix_storefront_customer_accounts_client_id",
        table_name="storefront_customer_accounts",
    )
    op.drop_index(
        "ix_storefront_customer_accounts_storefront_id",
        table_name="storefront_customer_accounts",
    )
    op.drop_table("storefront_customer_accounts")
