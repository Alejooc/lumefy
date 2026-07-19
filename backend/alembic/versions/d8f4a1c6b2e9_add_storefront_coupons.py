"""add storefront coupons

Revision ID: d8f4a1c6b2e9
Revises: c7a3e8b5d1f2
"""
from alembic import op
import sqlalchemy as sa
revision='d8f4a1c6b2e9';down_revision='c7a3e8b5d1f2';branch_labels=None;depends_on=None
def upgrade():
 op.create_table('storefront_coupons',sa.Column('storefront_id',sa.UUID(),sa.ForeignKey('storefronts.id'),nullable=False),sa.Column('code',sa.String(),nullable=False),sa.Column('discount_type',sa.String(),nullable=False),sa.Column('value',sa.Float(),nullable=False),sa.Column('minimum_amount',sa.Float(),nullable=False),sa.Column('starts_at',sa.DateTime(timezone=True)),sa.Column('ends_at',sa.DateTime(timezone=True)),sa.Column('is_enabled',sa.Boolean(),nullable=False),sa.Column('id',sa.UUID(),primary_key=True),sa.Column('created_at',sa.DateTime(),nullable=False),sa.Column('updated_at',sa.DateTime(),nullable=False),sa.Column('is_active',sa.Boolean(),nullable=False),sa.Column('created_by_id',sa.UUID()),sa.Column('updated_by_id',sa.UUID()),sa.Column('company_id',sa.UUID(),sa.ForeignKey('companies.id')))
def downgrade():op.drop_table('storefront_coupons')
