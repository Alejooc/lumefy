"""update_sales_for_b2b

Revision ID: 905babc95201
Revises: 7479ff534c8f
Create Date: 2026-02-10 14:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '905babc95201'
down_revision = '7479ff534c8f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new values to SaleStatus enum
    # PostgreSQL ENUM modification must be done outside of a transaction block usually, 
    # but Alembic runs in a transaction. We can use commit() to break out if needed, 
    # but `op.execute` inside standard migration usually works for ADD VALUE in recent PG versions 
    # if it's not in a transaction block (autocommit).
    # However, to be safe and simple, we try op.execute.
    
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE salestatus ADD VALUE IF NOT EXISTS 'QUOTE'")
        op.execute("ALTER TYPE salestatus ADD VALUE IF NOT EXISTS 'CONFIRMED'")
        op.execute("ALTER TYPE salestatus ADD VALUE IF NOT EXISTS 'DISPATCHED'")
        op.execute("ALTER TYPE salestatus ADD VALUE IF NOT EXISTS 'DELIVERED'")
    
    # Add new columns to sales table
    op.add_column('sales', sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('sales', sa.Column('shipping_address', sa.String(), nullable=True))
    op.add_column('sales', sa.Column('notes', sa.String(), nullable=True))
    op.add_column('sales', sa.Column('shipping_cost', sa.Float(), server_default='0.0', nullable=False))


def downgrade() -> None:
    # Remove columns
    op.drop_column('sales', 'shipping_cost')
    op.drop_column('sales', 'notes')
    op.drop_column('sales', 'shipping_address')
    op.drop_column('sales', 'valid_until')
    
    # We generally don't remove Enum values in downgrade as it's complex and often unnecessary data loss
    pass
