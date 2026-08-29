"""add automatic NPM provisioning state to storefront domains.

Revision ID: ft8d9e0f1a2b
Revises: fs7c8d9e0f1a
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ft8d9e0f1a2b"
down_revision: Union[str, None] = "fs7c8d9e0f1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "storefront_domains",
        sa.Column("provisioning_status", sa.String(length=32), nullable=False, server_default="PENDING_VERIFICATION"),
    )
    op.add_column(
        "storefront_domains",
        sa.Column("provisioning_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("storefront_domains", sa.Column("provisioning_error", sa.Text(), nullable=True))
    op.add_column("storefront_domains", sa.Column("provisioning_next_attempt_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("storefront_domains", sa.Column("provisioning_last_attempt_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("storefront_domains", sa.Column("npm_proxy_host_id", sa.Integer(), nullable=True))
    op.add_column("storefront_domains", sa.Column("npm_certificate_id", sa.Integer(), nullable=True))
    op.add_column("storefront_domains", sa.Column("provisioned_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "UPDATE storefront_domains SET provisioning_status = "
        "CASE WHEN is_active = false THEN 'REMOVED' "
        "WHEN is_verified = true THEN 'NOT_CONFIGURED' "
        "ELSE 'PENDING_VERIFICATION' END"
    )
    op.alter_column("storefront_domains", "provisioning_status", server_default=None)
    op.alter_column("storefront_domains", "provisioning_attempts", server_default=None)
    op.create_index(
        op.f("ix_storefront_domains_provisioning_status"),
        "storefront_domains",
        ["provisioning_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_storefront_domains_provisioning_next_attempt_at"),
        "storefront_domains",
        ["provisioning_next_attempt_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_storefront_domains_provisioning_next_attempt_at"), table_name="storefront_domains")
    op.drop_index(op.f("ix_storefront_domains_provisioning_status"), table_name="storefront_domains")
    op.drop_column("storefront_domains", "provisioned_at")
    op.drop_column("storefront_domains", "npm_certificate_id")
    op.drop_column("storefront_domains", "npm_proxy_host_id")
    op.drop_column("storefront_domains", "provisioning_last_attempt_at")
    op.drop_column("storefront_domains", "provisioning_next_attempt_at")
    op.drop_column("storefront_domains", "provisioning_error")
    op.drop_column("storefront_domains", "provisioning_attempts")
    op.drop_column("storefront_domains", "provisioning_status")
