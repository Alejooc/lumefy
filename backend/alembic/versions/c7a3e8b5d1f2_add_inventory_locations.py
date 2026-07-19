"""add inventory locations

Revision ID: c7a3e8b5d1f2
Revises: b6e2f9c4a8d1
"""
from alembic import op
import sqlalchemy as sa
revision='c7a3e8b5d1f2';down_revision='b6e2f9c4a8d1';branch_labels=None;depends_on=None
def upgrade():
 op.create_table('inventory_locations',sa.Column('branch_id',sa.UUID(),sa.ForeignKey('branches.id'),nullable=False),sa.Column('name',sa.String(),nullable=False),sa.Column('code',sa.String(),nullable=False),sa.Column('location_type',sa.String(),nullable=False),sa.Column('is_dispatch_location',sa.Boolean(),nullable=False),sa.Column('id',sa.UUID(),primary_key=True),sa.Column('created_at',sa.DateTime(),nullable=False),sa.Column('updated_at',sa.DateTime(),nullable=False),sa.Column('is_active',sa.Boolean(),nullable=False),sa.Column('created_by_id',sa.UUID()),sa.Column('updated_by_id',sa.UUID()),sa.Column('company_id',sa.UUID(),sa.ForeignKey('companies.id')),sa.UniqueConstraint('branch_id','code',name='uq_inventory_location_branch_code'))
def downgrade():op.drop_table('inventory_locations')
