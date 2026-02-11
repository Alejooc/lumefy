"""add is_warehouse and allow_pos to branch

Revision ID: 52ba3d1a4e2b
Revises: f3ba2a847c01
Create Date: 2026-02-11 09:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '52ba3d1a4e2b'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add columns to branches table
    # Check if column exists first or just add it (standard alembic)
    # Using add_column with server_default to handle existing rows
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('branches')]
    
    if 'is_warehouse' not in columns:
        op.add_column('branches', sa.Column('is_warehouse', sa.Boolean(), server_default='true', nullable=False))
        
    if 'allow_pos' not in columns:
        op.add_column('branches', sa.Column('allow_pos', sa.Boolean(), server_default='true', nullable=False))


def downgrade() -> None:
    op.drop_column('branches', 'allow_pos')
    op.drop_column('branches', 'is_warehouse')
