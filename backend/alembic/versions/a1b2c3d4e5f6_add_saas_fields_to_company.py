"""add_saas_fields_to_company

Revision ID: a1b2c3d4e5f6
Revises: 905babc95201
Create Date: 2026-02-10 16:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '905babc95201'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to companies table
    op.add_column('companies', sa.Column('plan', sa.String(), server_default='FREE', nullable=False))
    op.add_column('companies', sa.Column('valid_until', sa.String(), nullable=True))


def downgrade() -> None:
    # Remove columns
    op.drop_column('companies', 'valid_until')
    op.drop_column('companies', 'plan')
