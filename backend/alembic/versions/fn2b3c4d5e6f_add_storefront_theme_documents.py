"""add tenant-scoped storefront theme documents and revisions.

Revision ID: fn2b3c4d5e6f
Revises: fl1a2b3c4d5e
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "fn2b3c4d5e6f"
down_revision = "fl1a2b3c4d5e"
branch_labels = depends_on = None


UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "storefront_theme_documents",
        sa.Column("storefront_id", UUID, nullable=False),
        sa.Column("company_id", UUID, nullable=False),
        sa.Column("template_key", sa.String(length=80), nullable=False),
        sa.Column("draft_document", sa.JSON(), nullable=False),
        sa.Column("published_document", sa.JSON(), nullable=False),
        sa.Column("draft_version", sa.Integer(), nullable=False),
        sa.Column("published_version", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by_id", UUID, nullable=True),
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", UUID, nullable=True),
        sa.Column("updated_by_id", UUID, nullable=True),
        sa.ForeignKeyConstraint(
            ["storefront_id", "company_id"],
            ["storefronts.id", "storefronts.company_id"],
            name="fk_storefront_theme_document_storefront_tenant",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "storefront_id",
            "template_key",
            name="uq_storefront_theme_document_template",
        ),
    )
    op.create_index(
        "ix_storefront_theme_documents_storefront_id",
        "storefront_theme_documents",
        ["storefront_id"],
    )
    op.create_index(
        "ix_storefront_theme_documents_company_id",
        "storefront_theme_documents",
        ["company_id"],
    )

    op.create_table(
        "storefront_theme_revisions",
        sa.Column("theme_document_id", UUID, nullable=False),
        sa.Column("storefront_id", UUID, nullable=False),
        sa.Column("company_id", UUID, nullable=False),
        sa.Column("template_key", sa.String(length=80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("operation", sa.String(length=30), nullable=False),
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", UUID, nullable=True),
        sa.Column("updated_by_id", UUID, nullable=True),
        sa.ForeignKeyConstraint(
            ["theme_document_id"],
            ["storefront_theme_documents.id"],
            name="fk_storefront_theme_revision_document",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["storefront_id", "company_id"],
            ["storefronts.id", "storefronts.company_id"],
            name="fk_storefront_theme_revision_storefront_tenant",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "theme_document_id",
            "version",
            name="uq_storefront_theme_revision_version",
        ),
    )
    op.create_index(
        "ix_storefront_theme_revisions_theme_document_id",
        "storefront_theme_revisions",
        ["theme_document_id"],
    )
    op.create_index(
        "ix_storefront_theme_revisions_storefront_id",
        "storefront_theme_revisions",
        ["storefront_id"],
    )
    op.create_index(
        "ix_storefront_theme_revisions_company_id",
        "storefront_theme_revisions",
        ["company_id"],
    )

    # Seed one compatible document per active storefront. The service layer
    # expands the empty section list to the current component registry.
    op.execute(
        sa.text(
            """
            INSERT INTO storefront_theme_documents (
                id,
                storefront_id,
                company_id,
                template_key,
                draft_document,
                published_document,
                draft_version,
                published_version,
                published_at,
                published_by_id,
                created_at,
                updated_at,
                is_active,
                created_by_id,
                updated_by_id
            )
            SELECT
                gen_random_uuid(),
                storefront.id,
                storefront.company_id,
                'home',
                json_build_object(
                    'schema_version', 1,
                    'template', 'home',
                    'legacy_home', COALESCE(storefront.theme_settings -> 'home', '{}'::json),
                    'sections', '[]'::json
                ),
                json_build_object(
                    'schema_version', 1,
                    'template', 'home',
                    'legacy_home', COALESCE(storefront.theme_settings -> 'home', '{}'::json),
                    'sections', '[]'::json
                ),
                1,
                1,
                CURRENT_TIMESTAMP,
                storefront.updated_by_id,
                storefront.created_at,
                storefront.updated_at,
                storefront.is_active,
                storefront.created_by_id,
                storefront.updated_by_id
            FROM storefronts AS storefront
            WHERE storefront.is_active = TRUE
            """
        )
    )


def downgrade() -> None:
    op.drop_index(
        "ix_storefront_theme_revisions_company_id",
        table_name="storefront_theme_revisions",
    )
    op.drop_index(
        "ix_storefront_theme_revisions_storefront_id",
        table_name="storefront_theme_revisions",
    )
    op.drop_index(
        "ix_storefront_theme_revisions_theme_document_id",
        table_name="storefront_theme_revisions",
    )
    op.drop_table("storefront_theme_revisions")

    op.drop_index(
        "ix_storefront_theme_documents_company_id",
        table_name="storefront_theme_documents",
    )
    op.drop_index(
        "ix_storefront_theme_documents_storefront_id",
        table_name="storefront_theme_documents",
    )
    op.drop_table("storefront_theme_documents")
