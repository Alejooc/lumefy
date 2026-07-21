"""add secure storefront domain verification

Revision ID: e9a7d5c3b1f0
Revises: d8f4a1c6b2e9
"""

from alembic import op
import sqlalchemy as sa


revision = "e9a7d5c3b1f0"
down_revision = "d8f4a1c6b2e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("storefront_domains", sa.Column("verification_token", sa.String(), nullable=True))
    op.add_column("storefront_domains", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    # Historic rows were marked manually. Requiring one DNS verification makes
    # the domain ownership boundary enforceable from this release onward.
    op.execute("UPDATE storefront_domains SET is_verified = false")


def downgrade() -> None:
    op.drop_column("storefront_domains", "verified_at")
    op.drop_column("storefront_domains", "verification_token")
