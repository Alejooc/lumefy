"""add_pos_sessions_and_link_sales

Revision ID: b19d7c4a91f0
Revises: 7479ff534c8f, 891596236182, c9076a6d1ddc
Create Date: 2026-02-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b19d7c4a91f0'
down_revision: Union[str, Sequence[str], None] = ('7479ff534c8f', '891596236182', 'c9076a6d1ddc')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pos_sessions',
        sa.Column('branch_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.Enum('OPEN', 'CLOSED', name='possessionstatus'), nullable=False),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('opening_amount', sa.Float(), nullable=False),
        sa.Column('counted_amount', sa.Float(), nullable=False),
        sa.Column('expected_amount', sa.Float(), nullable=False),
        sa.Column('over_short', sa.Float(), nullable=False),
        sa.Column('closing_note', sa.String(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('updated_by_id', sa.UUID(), nullable=True),
        sa.Column('company_id', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], ),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pos_sessions_branch_id'), 'pos_sessions', ['branch_id'], unique=False)
    op.create_index(op.f('ix_pos_sessions_status'), 'pos_sessions', ['status'], unique=False)
    op.create_index(op.f('ix_pos_sessions_user_id'), 'pos_sessions', ['user_id'], unique=False)

    op.add_column('sales', sa.Column('pos_session_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_sales_pos_session_id'), 'sales', ['pos_session_id'], unique=False)
    op.create_foreign_key(None, 'sales', 'pos_sessions', ['pos_session_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint(None, 'sales', type_='foreignkey')
    op.drop_index(op.f('ix_sales_pos_session_id'), table_name='sales')
    op.drop_column('sales', 'pos_session_id')

    op.drop_index(op.f('ix_pos_sessions_user_id'), table_name='pos_sessions')
    op.drop_index(op.f('ix_pos_sessions_status'), table_name='pos_sessions')
    op.drop_index(op.f('ix_pos_sessions_branch_id'), table_name='pos_sessions')
    op.drop_table('pos_sessions')
    op.execute("DROP TYPE IF EXISTS possessionstatus")

