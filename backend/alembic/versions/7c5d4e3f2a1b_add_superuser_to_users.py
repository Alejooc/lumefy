"""add is_superuser to users

Revision ID: 7c5d4e3f2a1b
Revises: 52ba3d1a4e2b
Create Date: 2026-02-11 09:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7c5d4e3f2a1b'
down_revision = '52ba3d1a4e2b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_superuser column to users table
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('users')]
    
    if 'is_superuser' not in columns:
        op.add_column('users', sa.Column('is_superuser', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('users', 'is_superuser')
