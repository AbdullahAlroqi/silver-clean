"""add warehouses and break windows

Revision ID: 8f3c2b1a9d70
Revises: e7b9c2d4a6f1
Create Date: 2026-07-18 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '8f3c2b1a9d70'
down_revision = 'e7b9c2d4a6f1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('break_type', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('break_date', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('break_start_time', sa.Time(), nullable=True))
        batch_op.add_column(sa.Column('break_end_time', sa.Time(), nullable=True))

    op.create_table(
        'warehouse',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name_ar', sa.String(length=100), nullable=False),
        sa.Column('name_en', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'warehouse_cities',
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('city_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['city_id'], ['city.id']),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouse.id']),
        sa.PrimaryKeyConstraint('warehouse_id', 'city_id')
    )
    with op.batch_alter_table('product_stock') as batch_op:
        batch_op.alter_column('city_id', existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column('warehouse_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('price', sa.Float(), nullable=True))
        batch_op.create_foreign_key('fk_product_stock_warehouse_id', 'warehouse', ['warehouse_id'], ['id'])


def downgrade():
    with op.batch_alter_table('product_stock') as batch_op:
        batch_op.drop_constraint('fk_product_stock_warehouse_id', type_='foreignkey')
        batch_op.drop_column('price')
        batch_op.drop_column('warehouse_id')
        batch_op.alter_column('city_id', existing_type=sa.Integer(), nullable=False)
    op.drop_table('warehouse_cities')
    op.drop_table('warehouse')
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('break_end_time')
        batch_op.drop_column('break_start_time')
        batch_op.drop_column('break_date')
        batch_op.drop_column('break_type')
