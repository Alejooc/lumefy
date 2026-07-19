"""add accounting core

Revision ID: b6e2f9c4a8d1
Revises: a5d9e2c7b3f1
"""
from alembic import op
import sqlalchemy as sa
revision='b6e2f9c4a8d1'; down_revision='a5d9e2c7b3f1'; branch_labels=None; depends_on=None
def base(): return [sa.Column('id',sa.UUID(),primary_key=True),sa.Column('created_at',sa.DateTime(),nullable=False),sa.Column('updated_at',sa.DateTime(),nullable=False),sa.Column('is_active',sa.Boolean(),nullable=False),sa.Column('created_by_id',sa.UUID()),sa.Column('updated_by_id',sa.UUID()),sa.Column('company_id',sa.UUID(),sa.ForeignKey('companies.id'))]
def upgrade():
 op.create_table('chart_accounts',sa.Column('code',sa.String(),nullable=False),sa.Column('name',sa.String(),nullable=False),sa.Column('account_type',sa.Enum('ASSET','LIABILITY','EQUITY','INCOME','EXPENSE',name='accounttype'),nullable=False),*base())
 op.create_table('journal_entries',sa.Column('reference',sa.String()),sa.Column('memo',sa.String()),sa.Column('status',sa.Enum('DRAFT','POSTED','CANCELLED',name='journalentrystatus'),nullable=False),*base())
 op.create_table('journal_entry_lines',sa.Column('entry_id',sa.UUID(),sa.ForeignKey('journal_entries.id'),nullable=False),sa.Column('account_id',sa.UUID(),sa.ForeignKey('chart_accounts.id'),nullable=False),sa.Column('debit',sa.Float(),nullable=False),sa.Column('credit',sa.Float(),nullable=False),*base())
def downgrade(): op.drop_table('journal_entry_lines');op.drop_table('journal_entries');op.drop_table('chart_accounts');op.execute('drop type if exists accounttype');op.execute('drop type if exists journalentrystatus')
