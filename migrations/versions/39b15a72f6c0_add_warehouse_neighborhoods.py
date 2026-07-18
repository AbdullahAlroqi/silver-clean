"""add warehouse neighborhoods

Revision ID: 39b15a72f6c0
Revises: 8f3c2b1a9d70
Create Date: 2026-07-18 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '39b15a72f6c0'
down_revision = '8f3c2b1a9d70'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'warehouse_neighborhoods',
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('neighborhood_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['neighborhood_id'], ['neighborhood.id']),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouse.id']),
        sa.PrimaryKeyConstraint('warehouse_id', 'neighborhood_id')
    )


def downgrade():
    op.drop_table('warehouse_neighborhoods')
