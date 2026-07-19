"""add manufacturing

Revision ID: a5d9e2c7b3f1
Revises: f4b8c1e6a2d7
"""
from alembic import op
import sqlalchemy as sa
revision='a5d9e2c7b3f1'; down_revision='f4b8c1e6a2d7'; branch_labels=None; depends_on=None
def base_columns():
    return [sa.Column('id',sa.UUID(),primary_key=True),sa.Column('created_at',sa.DateTime(),nullable=False),sa.Column('updated_at',sa.DateTime(),nullable=False),sa.Column('is_active',sa.Boolean(),nullable=False),sa.Column('created_by_id',sa.UUID()),sa.Column('updated_by_id',sa.UUID()),sa.Column('company_id',sa.UUID(),sa.ForeignKey('companies.id'))]
def upgrade():
    op.create_table('bills_of_materials',sa.Column('product_id',sa.UUID(),sa.ForeignKey('products.id'),nullable=False),sa.Column('quantity',sa.Float(),nullable=False),*base_columns())
    op.create_table('bill_of_materials_lines',sa.Column('bom_id',sa.UUID(),sa.ForeignKey('bills_of_materials.id'),nullable=False),sa.Column('component_id',sa.UUID(),sa.ForeignKey('products.id'),nullable=False),sa.Column('quantity',sa.Float(),nullable=False),*base_columns())
    op.create_table('manufacturing_orders',sa.Column('bom_id',sa.UUID(),sa.ForeignKey('bills_of_materials.id'),nullable=False),sa.Column('branch_id',sa.UUID(),sa.ForeignKey('branches.id'),nullable=False),sa.Column('quantity',sa.Float(),nullable=False),sa.Column('status',sa.Enum('DRAFT','CONFIRMED','DONE','CANCELLED',name='manufacturingstatus'),nullable=False),*base_columns())
def downgrade():
    op.drop_table('manufacturing_orders'); op.drop_table('bill_of_materials_lines'); op.drop_table('bills_of_materials'); op.execute('DROP TYPE IF EXISTS manufacturingstatus')
