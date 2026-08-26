"""add tenant-scoped storefront media assets.

Revision ID: fo3c4d5e6f7a
Revises: fn2b3c4d5e6f
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "fo3c4d5e6f7a"
down_revision = "fn2b3c4d5e6f"
branch_labels = depends_on = None


UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "storefront_media_assets",
        sa.Column("storefront_id", UUID, nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("alt_text", sa.String(length=255), nullable=True),
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", UUID, nullable=True),
        sa.Column("updated_by_id", UUID, nullable=True),
        sa.Column("company_id", UUID, nullable=False),
        sa.ForeignKeyConstraint(
            ["storefront_id", "company_id"],
            ["storefronts.id", "storefronts.company_id"],
            name="fk_storefront_media_asset_storefront_tenant",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "storefront_id",
            "storage_path",
            name="uq_storefront_media_asset_storage_path",
        ),
    )
    op.create_index(
        "ix_storefront_media_assets_storefront_id",
        "storefront_media_assets",
        ["storefront_id"],
    )
    op.create_index(
        "ix_storefront_media_assets_company_id",
        "storefront_media_assets",
        ["company_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_storefront_media_assets_company_id",
        table_name="storefront_media_assets",
    )
    op.drop_index(
        "ix_storefront_media_assets_storefront_id",
        table_name="storefront_media_assets",
    )
    op.drop_table("storefront_media_assets")
